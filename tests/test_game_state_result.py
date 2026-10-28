import unittest

from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board, GARBAGE_CELL, PIECE_TO_CELL
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.model.back_to_back_source import BackToBackSource


class GameStateResultTests(unittest.TestCase):
    def test_quad_perfect_clear_awards_two_enabled_b2b_credits(self) -> None:
        cols = [15] * 10
        cols[4] = 0
        state = GameState(
            Board(cols=cols), spawn_location(Piece.I), [Piece.O], None, 0, 0
        )
        applied = state.apply_move(
            Placement(PieceLocation(Piece.I, Rotation.East, 4, 2), Spin.none),
            Rules(back_to_back_sources=frozenset(BackToBackSource)),
        )
        assert applied is not None
        self.assertTrue(applied.perfect_clear)
        self.assertEqual(applied.back_to_back_after, 2)

    def test_apply_move_returns_line_clear_facts(self) -> None:
        board = Board(cols=[1] * 8 + [0] * 2)
        state = GameState(
            board,
            spawn_location(Piece.O),
            [Piece.I],
            None,
            combo=2,
            back_to_back=3,
        )
        placement = Placement(PieceLocation(Piece.O, Rotation.North, 8, 0), Spin.none)

        result = state.apply_move(placement, Rules())

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.lines_cleared, 1)
        self.assertEqual(result.garbage_lines_cleared, 1)
        self.assertFalse(result.perfect_clear)
        self.assertEqual(result.combo_before, 2)
        self.assertEqual(result.combo_after, 3)
        self.assertEqual(result.back_to_back_before, 3)
        self.assertEqual(result.back_to_back_after, 0)

    def test_garbage_clear_count_uses_cell_provenance_before_rows_are_removed(
        self,
    ) -> None:
        board = Board.empty()
        board.rows[0][:8] = bytes([PIECE_TO_CELL[Piece.J]] * 8)
        board.rows[1][:8] = bytes([PIECE_TO_CELL[Piece.L]] * 8)
        board.rows[1][0] = GARBAGE_CELL
        # Garbage outside the clear does not contribute to this lock's count.
        board.set_cell(0, 3, GARBAGE_CELL)
        state = GameState(board, spawn_location(Piece.O), [Piece.I], None, 0, 0)
        result = state.apply_move(
            Placement(PieceLocation(Piece.O, Rotation.North, 8, 0), Spin.none), Rules()
        )
        assert result is not None
        self.assertEqual(result.lines_cleared, 2)
        self.assertEqual(result.garbage_lines_cleared, 1)
        self.assertEqual(state.board.cell(0, 1), GARBAGE_CELL)


if __name__ == "__main__":
    unittest.main()
