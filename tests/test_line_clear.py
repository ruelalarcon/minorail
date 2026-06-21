from __future__ import annotations

import unittest

from tetris.game.back_to_back import clear_sources
from tetris.game.line_clear import LineClear
from tetris.model.back_to_back_source import BackToBackSource
from tetris.model.board import Board
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


if __name__ == "__main__":
    unittest.main()
