import unittest
from time import sleep
from typing import Any, cast

from runner.engine_session import EngineSession
from runner.limits import EngineLimits
from runner.pathfinding import PathfindingOptions
from suggestion.contracts.suggestion_request import SuggestionRequest
from suggestion.contracts.suggestion_result import SuggestionResult
from suggestion.contracts.suggestion_status import SuggestionStatus
from tetris.model.location import PieceLocation
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin
from visualizers.null import NullVisualizer


class FakeSuggestionService:
    def __init__(self, *, delay: float = 0.0) -> None:
        self._delay = delay
        self._suggestions = 0
        self.requests: list[SuggestionRequest] = []

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
        pass


class EngineSessionLimitsTests(unittest.TestCase):
    def test_piece_limit_stops_after_limit_piece_locks(self) -> None:
        session = EngineSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=EngineLimits(piece_limit=2),
        )
        cast(Any, session)._service = FakeSuggestionService()

        stats = session.play_game()

        self.assertEqual(stats["status"], "piece_limit")
        self.assertEqual(stats["pieces"], 2)

    def test_time_limit_can_stop_before_first_suggestion(self) -> None:
        session = EngineSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=EngineLimits(time_limit_ms=1),
        )
        cast(Any, session)._service = FakeSuggestionService(delay=0.002)

        stats = session.play_game()

        self.assertEqual(stats["status"], "time_limit")

    def test_pathfinding_options_are_passed_to_suggestion_request(self) -> None:
        session = EngineSession(
            "fake-bot",
            settings=_settings(),
            visualizer=NullVisualizer(),
            limits=EngineLimits(piece_limit=1),
            pathfinding_options=PathfindingOptions(
                pathfinding=False,
                convert_sonic_drops=True,
            ),
        )
        service = FakeSuggestionService()
        cast(Any, session)._service = service

        session.play_game()

        self.assertEqual(len(service.requests), 1)
        self.assertFalse(service.requests[0].pathfinding)
        self.assertFalse(service.requests[0].convert_sonic_drops)


def _settings():
    return {
        "protocol": {
            "rules": {
                "randomizer": "seven_bag",
                "kickset": "srs",
                "rot180": True,
                "sonic_drop": "only",
                "allspin_b2b": False,
                "allclear_b2b": False,
                "spawn_x": 4,
                "spawn_y": 19,
            },
            "start": {"piece_stream_limit": 11},
        },
        "service": {"path": {"convert_sonic_drops": False}},
        "bot": {"suggest_timeout_ms": 10_000, "idle_ms": 60_000},
        "engine": {
            "randomizer": {"seed": 0},
            "queue": {"initial": 5, "refill_threshold": 5},
            "limits": {"piece_limit": None, "time_limit_ms": None},
        },
        "logging": {"bot_info": {"print": ["warning"]}},
    }


if __name__ == "__main__":
    unittest.main()
