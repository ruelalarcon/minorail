from __future__ import annotations

import unittest

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.kicks.registry import register_kick_table
from tetris.kicks.table import KickTable
from tetris.movegen.pathfinder import MoveStep, convert_sonic_drops, find_path
from tetris.movegen.rotation import try_rotate, try_rotate_180


class PathfinderTests(unittest.TestCase):
    def test_convert_sonic_drop_to_exact_soft_drop_count(self) -> None:
        path = [MoveStep.Right, MoveStep.SonicDrop, MoveStep.HardDrop]

        converted = convert_sonic_drops(path, Board(), Piece.O)

        self.assertEqual(
            converted,
            [MoveStep.Right] + [MoveStep.SoftDrop] * 20 + [MoveStep.HardDrop],
        )

    def test_convert_sonic_drop_uses_custom_spawn_y(self) -> None:
        path = [MoveStep.SonicDrop, MoveStep.HardDrop]

        converted = convert_sonic_drops(path, Board(), Piece.O, spawn_y=18)

        self.assertEqual(converted, [MoveStep.SoftDrop] * 18 + [MoveStep.HardDrop])

    def test_find_path_uses_custom_spawn_x(self) -> None:
        path = find_path(
            Board(),
            Piece.O,
            PieceLocation(Piece.O, Rotation.North, 4, 0),
            Rules(spawn_x=5),
        )

        self.assertEqual(path, [MoveStep.Left, MoveStep.HardDrop])

    def test_o_rotation_is_controlled_by_kick_table(self) -> None:
        board = Board()

        self.assertIsNone(
            try_rotate(
                board,
                Piece.O,
                Rotation.North,
                Rotation.East,
                4,
                19,
                "srs",
            )
        )

        register_kick_table(
            "test_o_kicks",
            KickTable(
                kicks={
                    Piece.O: {
                        (Rotation.North, Rotation.East): ((0, 0),),
                    }
                }
            ),
        )

        self.assertEqual(
            try_rotate(
                board,
                Piece.O,
                Rotation.North,
                Rotation.East,
                4,
                19,
                "test_o_kicks",
            ),
            (4, 19, Rotation.East),
        )

    def test_180_rotation_is_a_normal_transition(self) -> None:
        board = Board()

        self.assertEqual(
            try_rotate_180(board, Piece.T, Rotation.North, 4, 19, "srs"),
            (4, 19, Rotation.South),
        )

        register_kick_table(
            "test_180_kicks",
            KickTable(
                kicks={
                    Piece.T: {
                        (Rotation.North, Rotation.South): ((0, 0),),
                    }
                }
            ),
        )

        self.assertEqual(
            try_rotate_180(board, Piece.T, Rotation.North, 4, 19, "test_180_kicks"),
            (4, 19, Rotation.South),
        )

    def test_srs_zero_180_preserves_reachable_spin_path(self) -> None:
        board = Board(cols=[3, 7, 7, 7, 15, 6, 0, 3, 3, 7])
        target = PieceLocation(Piece.J, Rotation.West, 6, 1)

        path = find_path(
            board,
            Piece.J,
            target,
            Rules(kickset="srs", rot180=True, sonic_drop="only"),
        )

        self.assertEqual(
            path,
            [
                MoveStep.Right,
                MoveStep.Right,
                MoveStep.RotCW,
                MoveStep.SonicDrop,
                MoveStep.Rot180,
                MoveStep.HardDrop,
            ],
        )


if __name__ == "__main__":
    unittest.main()
