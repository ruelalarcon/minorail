import unittest

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
        self.assertEqual(result["events"][0]["type"], "piece_locked")
        self.assertEqual(result["events"][0]["combo_before"], 2)
        self.assertEqual(result["events"][0]["combo_after"], 3)
        self.assertEqual(result["events"][1]["type"], "game_ended")


if __name__ == "__main__":
    unittest.main()
