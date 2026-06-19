import unittest

from battle.attack.generic import GenericAttackCalculator
from tetris.game.state import AppliedMove
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin


class GenericAttackCalculatorTests(unittest.TestCase):
    def test_minorail_generic_attack_defaults(self) -> None:
        calc = GenericAttackCalculator()
        placement = Placement(PieceLocation(Piece.I, Rotation.North, 4, 0), Spin.none)

        result = calc.calculate(
            AppliedMove(
                placement=placement,
                lines_cleared=4,
                perfect_clear=True,
                combo_before=2,
                combo_after=3,
                back_to_back_before=1,
                back_to_back_after=2,
            )
        )

        self.assertEqual(result.breakdown["line_clear"], 4)
        self.assertEqual(result.breakdown["combo"], 2)
        self.assertEqual(result.breakdown["back_to_back"], 1)
        self.assertEqual(result.breakdown["perfect_clear"], 10)
        self.assertEqual(result.attack, 17)

    def test_t_spin_line_clear_values_are_explicit(self) -> None:
        calc = GenericAttackCalculator()
        placement = Placement(PieceLocation(Piece.T, Rotation.North, 4, 0), Spin.full)

        result = calc.calculate(
            AppliedMove(
                placement=placement,
                lines_cleared=2,
                perfect_clear=False,
                combo_before=0,
                combo_after=1,
                back_to_back_before=0,
                back_to_back_after=1,
            )
        )

        self.assertEqual(result.attack, 4)


if __name__ == "__main__":
    unittest.main()
