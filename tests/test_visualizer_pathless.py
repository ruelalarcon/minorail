import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from suggestion.contracts.suggestion_result import SuggestionResult
from suggestion.contracts.suggestion_status import SuggestionStatus
from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from visualizers.terminal import TerminalVisualizer
from visualizers.web import WebVisualizer


class PathlessVisualizerTests(unittest.TestCase):
    def test_terminal_pathless_result_does_not_warn(self) -> None:
        visualizer = TerminalVisualizer(_settings())
        state = _state()

        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            visualizer.animate_suggestion(
                state,
                Piece.T,
                _pathless_result(),
                hold_used=False,
                rules=Rules(),
            )

        self.assertEqual(stderr.getvalue(), "")

    def test_web_pathless_result_renders_selected_placement(self) -> None:
        visualizer = WebVisualizer(_settings())
        state = _state()

        with redirect_stderr(io.StringIO()):
            visualizer.animate_suggestion(
                state,
                Piece.T,
                _pathless_result(),
                hold_used=False,
                rules=Rules(),
            )

        frame = visualizer._current_frame()
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.status, "Placement selected")
        self.assertEqual(frame.active_x, 4)
        self.assertEqual(frame.active_y, 0)
        self.assertEqual(frame.active_rotation, Rotation.North)


def _state() -> GameState:
    return GameState(
        board=Board(),
        active=spawn_location(Piece.T),
        queue=[Piece.I, Piece.O],
        hold=None,
        combo=0,
        back_to_back=0,
    )


def _pathless_result() -> SuggestionResult:
    placement = Placement(
        PieceLocation(Piece.T, Rotation.North, 4, 0),
        Spin.none,
    )
    return SuggestionResult(
        seq=0,
        status=SuggestionStatus.Synced,
        placements=[placement],
        placement=placement,
        path=None,
    )


def _settings() -> dict[str, Any]:
    return {
        "visualizer": {
            "move_delay_ms": 0,
            "lock_delay_ms": 0,
            "first_move_delay_ms": 0,
            "visible_rows": 20,
            "queue_size": 5,
        }
    }


if __name__ == "__main__":
    unittest.main()
