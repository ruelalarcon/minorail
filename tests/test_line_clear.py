from __future__ import annotations

import unittest

from tetris.game.back_to_back import clear_sources
from tetris.game.line_clear import LineClear
from tetris.model.back_to_back_source import BackToBackSource
from tetris.model.board import (
    EMPTY_CELL,
    GARBAGE_CELL,
    PIECE_TO_CELL,
    Board,
    cell_label,
)
from tetris.model.piece import Piece
from tetris.model.rules import DEFAULT_BACK_TO_BACK_SOURCES, Rules
from tetris.model.spin import Spin
from tetris.model.spin_detection import SpinDetection


def full_bottom_row() -> Board:
    return Board(cols=[1] * 10)


class LineClearTests(unittest.TestCase):
    def test_default_rules_use_t_spins_and_guideline_back_to_back_sources(self) -> None:
        rules = Rules()

        self.assertEqual(rules.spin_detection, SpinDetection.t_spins)
        self.assertEqual(rules.back_to_back_sources, DEFAULT_BACK_TO_BACK_SOURCES)

    def test_t_spin_full_contributes_to_back_to_back_by_default(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.T,
            spin=Spin.full,
            rules=Rules(),
        )

        self.assertEqual(result.back_to_back, 3)

    def test_t_spin_mini_contributes_to_back_to_back_by_default(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.T,
            spin=Spin.mini,
            rules=Rules(),
        )

        self.assertEqual(result.back_to_back, 3)

    def test_non_t_spin_does_not_back_to_back_by_default(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.L,
            spin=Spin.full,
            rules=Rules(),
        )

        self.assertEqual(result.back_to_back, 0)

    def test_non_t_full_spin_back_to_backs_with_allspin_source(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.L,
            spin=Spin.full,
            rules=Rules(back_to_back_sources=frozenset({BackToBackSource.allspin})),
        )

        self.assertEqual(result.back_to_back, 3)

    def test_non_t_mini_spin_back_to_backs_with_allspin_mini_source(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.L,
            spin=Spin.mini,
            rules=Rules(
                back_to_back_sources=frozenset({BackToBackSource.allspin_mini})
            ),
        )

        self.assertEqual(result.back_to_back, 3)

    def test_t_full_and_mini_map_to_separate_sources(self) -> None:
        full = clear_sources(Piece.T, Spin.full, 1, False)
        mini = clear_sources(Piece.T, Spin.mini, 1, False)

        self.assertIn(BackToBackSource.t_spin, full)
        self.assertNotIn(BackToBackSource.t_spin_mini, full)
        self.assertIn(BackToBackSource.t_spin_mini, mini)
        self.assertNotIn(BackToBackSource.t_spin, mini)

    def test_perfect_clear_only_back_to_backs_with_perfect_clear_source(self) -> None:
        default_result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.I,
            spin=Spin.none,
            rules=Rules(back_to_back_sources=frozenset()),
        )
        perfect_clear_result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.I,
            spin=Spin.none,
            rules=Rules(
                back_to_back_sources=frozenset({BackToBackSource.perfect_clear})
            ),
        )

        self.assertEqual(default_result.back_to_back, 0)
        self.assertEqual(perfect_clear_result.back_to_back, 3)

    def test_back_to_back_sources_ordering_does_not_matter(self) -> None:
        first = Rules.from_values({"back_to_back_sources": ["perfect-clear", "quad"]})
        second = Rules.from_values({"back_to_back_sources": ["quad", "perfect-clear"]})

        self.assertEqual(first.back_to_back_sources, second.back_to_back_sources)

    def test_duplicate_back_to_back_sources_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Rules.from_values({"back_to_back_sources": ["quad", "quad"]})

    def test_board_distance_to_ground_supports_rows_above_64(self) -> None:
        board = Board(cols=[1 << 70, 0], height=100)

        self.assertEqual(board.distance_to_ground(0, 75), 4)
        self.assertEqual(board.distance_to_ground(1, 75), 75)

    def test_line_clear_supports_rows_above_64(self) -> None:
        board = Board(cols=[1 << 70, 1 << 70], height=100)

        self.assertEqual(board.line_clears(), 1 << 70)
        board.remove_lines(1 << 70)

        self.assertEqual(board.cols, [0, 0])

    def test_board_preserves_piece_cell_labels(self) -> None:
        board = Board.from_sbp([["I", "J", "L", "O", "S", "T", "Z", "G", 1]])

        self.assertEqual(
            [board.cell(x, 0) for x in range(9)],
            [
                PIECE_TO_CELL[Piece.I],
                PIECE_TO_CELL[Piece.J],
                PIECE_TO_CELL[Piece.L],
                PIECE_TO_CELL[Piece.O],
                PIECE_TO_CELL[Piece.S],
                PIECE_TO_CELL[Piece.T],
                PIECE_TO_CELL[Piece.Z],
                GARBAGE_CELL,
                GARBAGE_CELL,
            ],
        )
        self.assertEqual(
            [cell_label(board.cell(x, 0)) for x in range(9)], list("IJLOSTZGG")
        )

    def test_apply_garbage_accepts_arbitrary_rows(self) -> None:
        board = Board.empty(width=4, height=4)
        board.set_cell(1, 0, PIECE_TO_CELL[Piece.T])
        topped_out = board.apply_garbage(
            [
                [GARBAGE_CELL, EMPTY_CELL, GARBAGE_CELL, GARBAGE_CELL],
                [PIECE_TO_CELL[Piece.I], EMPTY_CELL, EMPTY_CELL, GARBAGE_CELL],
            ]
        )

        self.assertFalse(topped_out)
        self.assertEqual(
            board.rows[0],
            bytearray([GARBAGE_CELL, EMPTY_CELL, GARBAGE_CELL, GARBAGE_CELL]),
        )
        self.assertEqual(
            board.rows[1],
            bytearray([PIECE_TO_CELL[Piece.I], EMPTY_CELL, EMPTY_CELL, GARBAGE_CELL]),
        )
        self.assertEqual(board.cell(1, 2), PIECE_TO_CELL[Piece.T])


if __name__ == "__main__":
    unittest.main()
