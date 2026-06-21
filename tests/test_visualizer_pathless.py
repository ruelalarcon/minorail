import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from settings import VisualizerSettings
from contracts.suggestion_result import SuggestionResult
from contracts.suggestion_status import SuggestionStatus
from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from visualizers.solo.terminal import TerminalVisualizer
from visualizers.solo.web import WebVisualizer
from visualizers.battle.web import (
    _PlayerFrame,
    _battle_board_html,
    _garbage_cell_class,
)
from visualizers.battle.web import WebVisualizer as BattleWebVisualizer


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

    def test_battle_web_pathless_result_renders_selected_placement(self) -> None:
        visualizer = BattleWebVisualizer(_settings())
        state = _state()
        states = {"A": state, "B": _state(Piece.I)}
        incoming = {"A": 0, "B": 3}

        with redirect_stderr(io.StringIO()):
            visualizer.animate_suggestion(
                "A",
                states,
                incoming,
                Piece.T,
                _pathless_result(),
                hold_used=False,
                rules=Rules(),
            )

        frame = visualizer._current_frame()
        self.assertIsNotNone(frame)
        assert frame is not None
        player = frame.players["A"]
        self.assertEqual(player.status, "Placement selected")
        self.assertEqual(player.board.active_x, 4)
        self.assertEqual(player.board.active_y, 0)
        self.assertEqual(player.board.active_rotation, Rotation.North)
        self.assertEqual(frame.players["B"].incoming_garbage, 3)
        self.assertEqual(frame.players["B"].status, "")

    def test_battle_web_garbage_meter_wraps_visible_rows(self) -> None:
        classes = [_garbage_cell_class(row, 25, 20) for row in reversed(range(20))]

        self.assertEqual(classes.count("minorail-garbage-cell-layer-0"), 0)
        self.assertEqual(
            classes.count("minorail-garbage-cell minorail-garbage-cell-layer-0"),
            15,
        )
        self.assertEqual(
            classes.count("minorail-garbage-cell minorail-garbage-cell-layer-1"),
            5,
        )

    def test_battle_web_garbage_meter_html_uses_wrapped_layers(self) -> None:
        visualizer = BattleWebVisualizer(_settings())
        state = _state()
        visualizer._render({"A": state}, {"A": 25})
        frame = visualizer._current_frame()
        self.assertIsNotNone(frame)
        assert frame is not None

        html = _battle_board_html(
            _PlayerFrame(
                name="A",
                board=frame.players["A"].board,
                incoming_garbage=25,
                status="",
            )
        )

        self.assertEqual(html.count("minorail-garbage-cell-layer-0"), 19)
        self.assertEqual(html.count("minorail-garbage-cell-layer-1"), 3)


def _state(piece: Piece = Piece.T) -> GameState:
    return GameState(
        board=Board(),
        active=spawn_location(piece),
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


def _settings() -> VisualizerSettings:
    return VisualizerSettings(
        move_delay_ms=0,
        lock_delay_ms=0,
        first_move_delay_ms=0,
        visible_rows=22,
        queue_size=5,
    )


if __name__ == "__main__":
    unittest.main()
