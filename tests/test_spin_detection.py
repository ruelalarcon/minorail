from __future__ import annotations

import unittest

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.model.spin_detection import SpinDetection
from tetris.spin import detect_spin


def board_with(cells: set[tuple[int, int]]) -> Board:
    board = Board()
    for x, y in cells:
        board.cols[x] |= 1 << y
    return board


class SpinDetectionTests(unittest.TestCase):
    def test_none_never_spins(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.L, Rotation.North, 4, 0),
            immobile_l_board(),
            rules=Rules(spin_detection=SpinDetection.none),
            rotated=True,
        )

        self.assertEqual(spin, Spin.none)

    def test_all_mini_plus_immobile_non_t_returns_mini(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.L, Rotation.North, 4, 0),
            immobile_l_board(),
            rules=Rules(spin_detection=SpinDetection.all_mini_plus),
            rotated=True,
        )

        self.assertEqual(spin, Spin.mini)

    def test_all_plus_immobile_non_t_returns_full(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.L, Rotation.North, 4, 0),
            immobile_l_board(),
            rules=Rules(spin_detection=SpinDetection.all_plus),
            rotated=True,
        )

        self.assertEqual(spin, Spin.full)

    def test_t_spins_plus_immobile_t_fallback_returns_mini(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.T, Rotation.North, 4, 5),
            immobile_t_board(),
            rules=Rules(spin_detection=SpinDetection.t_spins_plus),
            rotated=True,
        )

        self.assertEqual(spin, Spin.mini)

    def test_all_mini_t_with_failed_corner_rule_does_not_use_immobility(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.T, Rotation.North, 4, 5),
            immobile_t_board(),
            rules=Rules(spin_detection=SpinDetection.all_mini),
            rotated=True,
        )

        self.assertEqual(spin, Spin.none)

    def test_immobility_includes_upward_movement_check(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.L, Rotation.North, 4, 0),
            board_with({(2, 0), (6, 0)}),
            rules=Rules(spin_detection=SpinDetection.all_plus),
            rotated=True,
        )

        self.assertEqual(spin, Spin.none)

    def test_immobility_does_not_require_downward_obstruction(self) -> None:
        spin = detect_spin(
            PieceLocation(Piece.L, Rotation.North, 4, 5),
            board_with({(2, 5), (6, 5), (3, 6)}),
            rules=Rules(spin_detection=SpinDetection.all_plus),
            rotated=True,
        )

        self.assertEqual(spin, Spin.full)


def immobile_l_board() -> Board:
    return board_with({(2, 0), (6, 0), (3, 1), (4, 1), (5, 1)})


def immobile_t_board() -> Board:
    return board_with({(2, 5), (6, 5), (3, 4), (4, 7)})


if __name__ == "__main__":
    unittest.main()
