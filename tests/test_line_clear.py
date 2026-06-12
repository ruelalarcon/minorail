from __future__ import annotations

import unittest

from tetris.game.line_clear import LineClear
from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rules import Rules
from tetris.model.spin import Spin


def full_bottom_row() -> Board:
    return Board(cols=[1] * 10)


class LineClearTests(unittest.TestCase):
    def test_t_spin_full_contributes_to_b2b_without_allspin_b2b(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.T,
            spin=Spin.full,
            rules=Rules(allspin_b2b=False),
        )

        self.assertEqual(result.back_to_back, 3)

    def test_t_spin_mini_contributes_to_b2b_without_allspin_b2b(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.T,
            spin=Spin.mini,
            rules=Rules(allspin_b2b=False),
        )

        self.assertEqual(result.back_to_back, 3)

    def test_non_t_spin_requires_allspin_b2b(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.L,
            spin=Spin.full,
            rules=Rules(allspin_b2b=False),
        )

        self.assertEqual(result.back_to_back, 0)

    def test_non_t_spin_contributes_to_b2b_with_allspin_b2b(self) -> None:
        result = LineClear.apply(
            full_bottom_row(),
            combo=0,
            back_to_back=2,
            piece=Piece.L,
            spin=Spin.full,
            rules=Rules(allspin_b2b=True),
        )

        self.assertEqual(result.back_to_back, 3)


if __name__ == "__main__":
    unittest.main()
