import unittest

from battle.evaluation.batch import _batch_summary as battle_batch_summary
from battle.evaluation.collector import EvaluationCollector as BattleCollector
from battle.runner.events import (
    GameEndedEvent as BattleGameEndedEvent,
    GameStartedEvent as BattleGameStartedEvent,
    PieceLockedEvent as BattlePieceLockedEvent,
)
from solo.evaluation.batch import _batch_summary as solo_batch_summary
from solo.evaluation.collector import EvaluationCollector
from solo.runner.events import GameEndedEvent, GameStartedEvent, PieceLockedEvent
from tetris.game.state import AppliedMove
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin


class EvaluationCollectorTests(unittest.TestCase):
    def test_collector_records_events_and_summary_rollups(self) -> None:
        collector = EvaluationCollector()
        placement = Placement(
            PieceLocation(Piece.T, Rotation.South, 4, 1),
            Spin.full,
        )

        collector.on_game_started(GameStartedEvent(session_id="eval-1", seed=123))
        collector.on_piece_locked(
            PieceLockedEvent(
                session_id="eval-1",
                piece_index=0,
                placement=placement,
                hold_used=True,
                applied=AppliedMove(
                    placement=placement,
                    lines_cleared=2,
                    perfect_clear=False,
                    combo_before=2,
                    combo_after=3,
                    back_to_back_before=5,
                    back_to_back_after=6,
                ),
                stack_height=17,
                occupied_cells=86,
                attack=3,
            )
        )
        collector.on_game_ended(
            GameEndedEvent(
                session_id="eval-1",
                status="topout",
                pieces=1,
                elapsed=0.5,
                pps=2.0,
                stack_height=21,
                occupied_cells=90,
            )
        )

        result = collector.result(game=0)

        self.assertEqual(result["seed"], 123)
        self.assertEqual(result["summary"]["status"], "topout")
        self.assertEqual(result["summary"]["lines_cleared"], 2)
        self.assertEqual(result["summary"]["line_clear_placements"], 1)
        self.assertEqual(result["summary"]["combo_steps"], 1)
        self.assertEqual(result["summary"]["back_to_back_steps"], 1)
        self.assertEqual(result["summary"]["holds"], 1)
        self.assertEqual(result["summary"]["attack"], 3)
        self.assertEqual(result["summary"]["max_attack"], 3)
        self.assertEqual(result["summary"]["attack_placements"], 1)
        self.assertEqual(result["events"][0]["type"], "piece_locked")
        self.assertEqual(result["events"][0]["combo_before"], 2)
        self.assertEqual(result["events"][0]["combo_after"], 3)
        self.assertEqual(result["events"][0]["attack"], 3)
        self.assertEqual(result["events"][1]["type"], "game_ended")

    def test_solo_batch_summary_uses_cumulative_names_only(self) -> None:
        games = [
            {
                "summary": {
                    "status": "piece_limit",
                    "pieces": 10,
                    "elapsed_ms": 5000,
                    "lines_cleared": 4,
                    "line_clear_placements": 2,
                    "combo_steps": 1,
                    "max_combo": 1,
                    "back_to_back_steps": 1,
                    "max_back_to_back": 2,
                    "attack": 6,
                    "max_attack": 4,
                    "attack_placements": 2,
                    "perfect_clears": 1,
                    "holds": 3,
                }
            }
        ]

        summary = solo_batch_summary(games)

        self.assertEqual(summary["pieces"], 10)
        self.assertEqual(summary["elapsed_ms"], 5000)
        self.assertEqual(summary["average_pps"], 2.0)
        self.assertNotIn("total_pieces", summary)
        self.assertNotIn("average_pieces", summary)
        self.assertNotIn("min_pieces", summary)
        self.assertNotIn("max_pieces", summary)
        self.assertNotIn("total_elapsed_ms", summary)
        self.assertNotIn("average_elapsed_ms", summary)

    def test_battle_collector_records_solo_parity_rollups(self) -> None:
        collector = BattleCollector()
        placement = Placement(
            PieceLocation(Piece.T, Rotation.South, 4, 1),
            Spin.full,
        )

        collector.on_game_started(
            BattleGameStartedEvent(
                session_id="battle-eval-1",
                seed=123,
                players=("A", "B"),
            )
        )
        collector.on_piece_locked(
            BattlePieceLockedEvent(
                session_id="battle-eval-1",
                player="A",
                piece_index=0,
                placement=placement,
                hold_used=True,
                applied=AppliedMove(
                    placement=placement,
                    lines_cleared=2,
                    perfect_clear=True,
                    combo_before=2,
                    combo_after=3,
                    back_to_back_before=5,
                    back_to_back_after=6,
                ),
                stack_height=17,
                occupied_cells=86,
                attack=3,
                incoming_garbage_before=4,
                garbage_cancelled=1,
                garbage_sent=2,
                incoming_garbage_after=3,
            )
        )
        collector.on_game_ended(
            BattleGameEndedEvent(
                session_id="battle-eval-1",
                status="topout",
                winner="B",
                loser="A",
                pieces={"A": 1, "B": 0},
                elapsed=0.5,
                pps=2.0,
                stack_height={"A": 21, "B": 0},
                occupied_cells={"A": 90, "B": 0},
                incoming_garbage={"A": 3, "B": 0},
            )
        )

        result = collector.result(game=0)
        summary = result["summary"]

        self.assertEqual(summary["pieces"], 1)
        self.assertEqual(summary["player_pieces"], {"A": 1, "B": 0})
        self.assertEqual(summary["combo_steps"], {"A": 1, "B": 0})
        self.assertEqual(summary["back_to_back_steps"], {"A": 1, "B": 0})
        self.assertEqual(summary["attack"], {"A": 3, "B": 0})
        self.assertEqual(summary["max_attack"], {"A": 3, "B": 0})
        self.assertEqual(summary["attack_placements"], {"A": 1, "B": 0})
        self.assertEqual(summary["perfect_clears"], {"A": 1, "B": 0})
        self.assertNotIn("total_pieces", summary)

    def test_battle_batch_summary_matches_solo_metrics(self) -> None:
        games = [
            {
                "summary": {
                    "status": "topout",
                    "winner": "A",
                    "pieces": 3,
                    "player_pieces": {"A": 2, "B": 1},
                    "elapsed_ms": 1500,
                    "lines_cleared": {"A": 2, "B": 0},
                    "line_clear_placements": {"A": 1, "B": 0},
                    "combo_steps": {"A": 1, "B": 0},
                    "max_combo": {"A": 2, "B": 0},
                    "back_to_back_steps": {"A": 1, "B": 0},
                    "max_back_to_back": {"A": 3, "B": 0},
                    "attack": {"A": 4, "B": 0},
                    "max_attack": {"A": 4, "B": 0},
                    "attack_placements": {"A": 1, "B": 0},
                    "perfect_clears": {"A": 1, "B": 0},
                    "holds": {"A": 1, "B": 0},
                    "garbage_sent": {"A": 2, "B": 0},
                    "garbage_cancelled": {"A": 1, "B": 0},
                    "garbage_applied": {"A": 0, "B": 2},
                    "max_incoming_garbage": {"A": 3, "B": 2},
                }
            }
        ]

        summary = battle_batch_summary(games)

        self.assertEqual(summary["pieces"], 3)
        self.assertEqual(summary["player_pieces"], {"A": 2, "B": 1})
        self.assertEqual(summary["elapsed_ms"], 1500)
        self.assertEqual(summary["average_pps"], 2.0)
        self.assertEqual(summary["combo_steps"], {"A": 1, "B": 0})
        self.assertEqual(summary["max_attack"], {"A": 4, "B": 0})
        self.assertEqual(summary["max_incoming_garbage"], {"A": 3, "B": 2})
        self.assertNotIn("total_pieces", summary)
        self.assertNotIn("average_pieces", summary)
        self.assertNotIn("total_elapsed_ms", summary)
        self.assertNotIn("average_elapsed_ms", summary)


if __name__ == "__main__":
    unittest.main()
