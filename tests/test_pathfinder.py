from __future__ import annotations

import unittest

from core.board import Board
from core.piece import Piece
from movegen.pathfinder import MoveStep, convert_sonic_drops


class PathfinderTests(unittest.TestCase):
    def test_convert_sonic_drop_to_exact_soft_drop_count(self) -> None:
        path = [MoveStep.Right, MoveStep.SonicDrop, MoveStep.HardDrop]

        converted = convert_sonic_drops(path, Board(), Piece.O)

        self.assertEqual(
            converted,
            [MoveStep.Right] + [MoveStep.SoftDrop] * 19 + [MoveStep.HardDrop],
        )


if __name__ == "__main__":
    unittest.main()
