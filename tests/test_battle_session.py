import unittest

from battle.runner.session import Session as BattleSession
from visualizers.battle.null import NullVisualizer
from contracts.observed_snapshot import ObservedSnapshot
from contracts.suggestion_request import SuggestionRequest
from contracts.suggestion_result import SuggestionResult
from contracts.suggestion_status import SuggestionStatus
from settings import RunLimits, Settings
from tetris.attack.registry import attack_calculator, register_attack_calculator
from tetris.game.state import AppliedMove
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin


class FixedAttackCalculator:
    def calculate(self, applied: AppliedMove) -> int:
        return 2


class FakeSuggestionService:
    def __init__(self) -> None:
        self.requests: list[SuggestionRequest] = []
        self.begun: list[tuple[str, Placement]] = []
        self.finished: list[tuple[str, list[Piece]]] = []
        self.stopped_games: list[str] = []
        self.closed = False

    def suggest(self, request: SuggestionRequest) -> SuggestionResult:
        self.requests.append(request)
        piece = request.snapshot.active.piece
        placement = Placement(PieceLocation(piece, Rotation.North, 4, 0), Spin.none)
        return SuggestionResult(
            seq=request.snapshot.seq,
            status=SuggestionStatus.Synced,
            placements=[placement],
            placement=placement,
            path=None,
        )

    def begin_advance(
        self, session_id: str, *, placement: Placement, rules: Rules
    ) -> bool:
        self.begun.append((session_id, placement))
        return True

    def finish_advance(
        self,
        session_id: str,
        *,
        snapshot: ObservedSnapshot,
        rules: Rules,
        new_pieces: list[Piece],
    ) -> None:
        self.finished.append((session_id, list(new_pieces)))

    def close(self) -> None:
        self.closed = True

    def stop_game(self, session_id: str) -> None:
        self.stopped_games.append(session_id)


class BattleSessionTests(unittest.TestCase):
    def test_piece_limit_stops_battle_and_stops_both_bot_games(self) -> None:
        service_a = FakeSuggestionService()
        service_b = FakeSuggestionService()
        session = BattleSession(
            "fake-a",
            "fake-b",
            settings=_settings(),
            visualizer=NullVisualizer(),
            service_a=service_a,
            service_b=service_b,
            limits=RunLimits(piece_limit=2),
            random_seed=0,
        )

        stats = session.play_game()

        self.assertEqual(stats["status"], "piece_limit")
        self.assertEqual(stats["pieces"], {"A": 1, "B": 1})
        self.assertEqual([advance[0] for advance in service_a.begun], ["battle:A"])
        self.assertEqual([advance[0] for advance in service_b.begun], ["battle:B"])
        self.assertEqual([advance[0] for advance in service_a.finished], ["battle:A"])
        self.assertEqual([advance[0] for advance in service_b.finished], ["battle:B"])
        self.assertEqual(service_a.stopped_games, ["battle:A"])
        self.assertEqual(service_b.stopped_games, ["battle:B"])
        self.assertFalse(service_a.closed)
        self.assertFalse(service_b.closed)

    def test_incoming_garbage_chunks_are_sent_to_battle_bot(self) -> None:
        _register_fixed_attack_calculator()
        service_a = FakeSuggestionService()
        service_b = FakeSuggestionService()
        session = BattleSession(
            "fake-a",
            "fake-b",
            settings=_settings(attack_calculator="test_fixed_attack"),
            visualizer=NullVisualizer(),
            service_a=service_a,
            service_b=service_b,
            limits=RunLimits(piece_limit=2),
            random_seed=0,
        )

        session.play_game()

        self.assertEqual(service_a.requests[0].incoming_garbage, [])
        self.assertEqual(service_b.requests[0].incoming_garbage, [2])


def _settings(*, attack_calculator: str = "tetrio_s2") -> Settings:
    return Settings.from_values(
        {
            "protocol": {
                "rules": {
                    "randomizer": "seven_bag",
                    "kickset": "srs",
                    "rot180": True,
                    "sonic_drop": "only",
                    "spin_detection": "t-spins",
                    "back_to_back_sources": ["quad", "t-spin", "t-spin-mini"],
                    "spawn_position": {"x": 4, "y": 20},
                },
                "start": {"piece_stream_limit": 11},
            },
            "service": {"path": {"convert_sonic_drops": False}},
            "bot": {"suggest_timeout_ms": 10_000, "idle_ms": 60_000},
            "game": {
                "attack": {"calculator": attack_calculator},
                "randomizer": {"seed": 0},
                "queue": {"initial": 5, "refill_threshold": 5},
                "limits": {"piece_limit": None, "time_limit_ms": None},
            },
            "logging": {"bot_info": {"print": ["warning"]}},
            "battle": {
                "garbage": {"rules": "tetrio"},
            },
        }
    )


def _register_fixed_attack_calculator() -> None:
    try:
        attack_calculator("test_fixed_attack")
    except ValueError:
        register_attack_calculator("test_fixed_attack", FixedAttackCalculator)


if __name__ == "__main__":
    unittest.main()
