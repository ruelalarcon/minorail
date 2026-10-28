from __future__ import annotations

import unittest

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.model.spin_detection import SpinDetection
from tetris.kicks.registry import register_kick_table
from tetris.kicks.table import KickTable
from tetris.movegen.pathfinder import MoveStep, convert_sonic_drops, find_path
from tetris.movegen.rotation import try_rotate, try_rotate_180


class PathfinderTests(unittest.TestCase):
    def test_mini_path_earns_spin_instead_of_only_reaching_its_cells(self) -> None:
        board = Board(cols=[0, 1, 1, 1, 1, 3, 1, 1, 1, 1])
        rules = Rules(
            kickset="srs_plus", spawn_y=21, spin_detection=SpinDetection.all_mini_plus
        )
        target = PieceLocation(Piece.T, Rotation.East, 0, 1)
        geometry = find_path(board, Piece.T, target, rules)
        self.assertEqual(
            geometry, [MoveStep.RotCW, MoveStep.DasLeft, MoveStep.HardDrop]
        )
        spin = find_path(board, Piece.T, target, rules, required_spin=Spin.mini)
        self.assertEqual(
            spin,
            [MoveStep.DasLeft, MoveStep.SonicDrop, MoveStep.RotCW, MoveStep.HardDrop],
        )
        ordinary = find_path(board, Piece.T, target, rules, required_spin=Spin.none)
        self.assertEqual(ordinary, geometry)

    def test_hard_drop_carries_airborne_spin_but_sonic_drop_clears_it(self) -> None:
        board = Board(cols=[511, 511, 511, 255, 255, 384, 319, 63, 63, 127])
        rules = Rules(
            kickset="srs_plus", spawn_y=21, spin_detection=SpinDetection.all_mini_plus
        )
        target = PieceLocation(Piece.I, Rotation.East, 5, 2)
        mini = [
            MoveStep.DasRight,
            MoveStep.RotCW,
            MoveStep.SonicDrop,
            MoveStep.RotCCW,
            MoveStep.RotCW,
            MoveStep.HardDrop,
        ]
        self.assertEqual(find_path(board, Piece.I, target, rules), mini)
        self.assertEqual(
            find_path(board, Piece.I, target, rules, required_spin=Spin.mini), mini
        )
        self.assertEqual(
            find_path(board, Piece.I, target, rules, required_spin=Spin.none),
            mini[:-1] + [MoveStep.SonicDrop, MoveStep.HardDrop],
        )

    def test_spin_constraint_rejects_a_geometrically_reachable_nonspin(self) -> None:
        target = PieceLocation(Piece.T, Rotation.North, 4, 0)
        self.assertIsNotNone(find_path(Board(), Piece.T, target, Rules()))
        self.assertIsNone(
            find_path(Board(), Piece.T, target, Rules(), required_spin=Spin.full)
        )

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

    def test_find_path_prefers_horizontal_steps_before_rotations(self) -> None:
        path = find_path(
            Board(),
            Piece.T,
            PieceLocation(Piece.T, Rotation.East, 5, 1),
            Rules(),
        )

        self.assertEqual(
            path,
            [MoveStep.Right, MoveStep.RotCW, MoveStep.HardDrop],
        )

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
