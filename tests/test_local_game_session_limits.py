import unittest
from time import sleep
from typing import Any, cast

from contracts.suggestion_request import SuggestionRequest
from contracts.suggestion_result import SuggestionResult
from contracts.suggestion_status import SuggestionStatus
from settings import PathSettings, RunLimits, Settings
from solo.runner.session import LocalGameSession
from tetris.attack.registry import attack_calculator, register_attack_calculator
from tetris.game.state import AppliedMove, GameState
from tetris.model.location import PieceLocation
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin
from visualizers.solo.null import NullVisualizer


class FixedAttackCalculator:
    def calculate(self, applied: AppliedMove) -> int:
        return 2


class CaptureTotalAttackVisualizer(NullVisualizer):
    def __init__(self) -> None:
        self.total_attacks: list[int] = []

    def on_piece_locked(self, state: GameState, *, total_attack: int) -> None:
        self.total_attacks.append(total_attack)


class FakeSuggestionService:
    def __init__(self, *, delay: float = 0.0) -> None:
        self._delay = delay
        self._suggestions = 0
        self.requests: list[SuggestionRequest] = []
        self.stopped_games: list[str] = []
        self.closed = False

    def suggest(self, request: SuggestionRequest) -> SuggestionResult:
        self.requests.append(request)
        if self._delay:
            sleep(self._delay)
        piece = request.snapshot.active.piece
        placement = Placement(
            PieceLocation(piece, Rotation.North, 4, self._suggestions * 4),
            Spin.none,
        )
        self._suggestions += 1
        return SuggestionResult(
            seq=request.snapshot.seq,
            status=SuggestionStatus.Synced,
            placements=[placement],
            placement=placement,
            path=None,
        )

    def close(self) -> None:
        self.closed = True

    def stop_game(self, session_id: str) -> None:
        self.stopped_games.append(session_id)


class LocalGameSessionLimitsTests(unittest.TestCase):
    def test_piece_limit_stops_after_limit_piece_locks(self) -> None:
        service = FakeSuggestionService()
        session = LocalGameSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=RunLimits(piece_limit=2),
            suggestion_service=service,
        )

        stats = session.play_game()

        self.assertEqual(stats["status"], "piece_limit")
        self.assertEqual(stats["pieces"], 2)
        self.assertEqual([r.incoming_garbage for r in service.requests], [[], []])
        self.assertEqual(service.stopped_games, ["terminal"])
        self.assertFalse(service.closed)

    def test_time_limit_can_stop_before_first_suggestion(self) -> None:
        service = FakeSuggestionService(delay=0.002)
        session = LocalGameSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=RunLimits(time_limit_ms=1),
            suggestion_service=service,
        )

        stats = session.play_game()

        self.assertEqual(stats["status"], "time_limit")

    def test_path_settings_are_passed_to_suggestion_request(self) -> None:
        service = FakeSuggestionService()
        session = LocalGameSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=RunLimits(piece_limit=1),
            pathfinding=PathSettings(
                pathfinding=False,
                convert_sonic_drops=True,
            ),
            suggestion_service=service,
        )

        session.play_game()

        self.assertEqual(len(service.requests), 1)
        self.assertFalse(service.requests[0].pathfinding)
        self.assertFalse(service.requests[0].convert_sonic_drops)

    def test_visualizer_receives_cumulative_total_attack(self) -> None:
        _register_fixed_attack_calculator()
        service = FakeSuggestionService()
        visualizer = CaptureTotalAttackVisualizer()
        session = LocalGameSession(
            "fake-bot",
            settings=_settings(attack_calculator="test_fixed_attack"),
            visualizer=visualizer,
            limits=RunLimits(piece_limit=2),
            suggestion_service=service,
        )

        session.play_game()

        self.assertEqual(visualizer.total_attacks, [2, 4])

    def test_owned_service_is_closed_after_game(self) -> None:
        service = FakeSuggestionService()
        session = LocalGameSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=RunLimits(piece_limit=1),
        )
        cast(Any, session)._service = service

        session.play_game()

        self.assertEqual(service.stopped_games, ["terminal"])
        self.assertTrue(service.closed)


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
        }
    )


def _register_fixed_attack_calculator() -> None:
    try:
        attack_calculator("test_fixed_attack")
    except ValueError:
        register_attack_calculator("test_fixed_attack", FixedAttackCalculator)


if __name__ == "__main__":
    unittest.main()
