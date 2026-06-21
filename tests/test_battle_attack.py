import unittest

from tetris.attack.classic_guideline import ClassicGuidelineAttackCalculator
from tetris.attack.modern_guideline import ModernGuidelineAttackCalculator
from tetris.attack.ppt import PptAttackCalculator
from tetris.attack.registry import attack_calculator, register_attack_calculator
from tetris.attack.tetrio_s1 import TetrioS1AttackCalculator
from tetris.attack.tetrio_s2 import TetrioS2AttackCalculator
from tetris.game.state import AppliedMove
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin


class BattleAttackRegistryTests(unittest.TestCase):
    def test_registry_resolves_only_named_attack_calculators(self) -> None:
        self.assertIs(attack_calculator("tetrio_s1"), TetrioS1AttackCalculator)
        self.assertIs(attack_calculator("tetrio_s2"), TetrioS2AttackCalculator)
        self.assertIs(
            attack_calculator("classic_guideline"), ClassicGuidelineAttackCalculator
        )
        self.assertIs(
            attack_calculator("modern_guideline"), ModernGuidelineAttackCalculator
        )
        self.assertIs(attack_calculator("ppt"), PptAttackCalculator)

        with self.assertRaises(ValueError):
            attack_calculator("generic")

    def test_duplicate_registration_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            register_attack_calculator("tetrio_s2", TetrioS2AttackCalculator)

    def test_unknown_attack_calculator_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            attack_calculator("missing")


class TetrioS2AttackCalculatorTests(unittest.TestCase):
    def test_minorail_combo_after_1_normalizes_to_combo_0(self) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.I, lines=4, combo_after=1)
        )

        self.assertEqual(attack, 4)

    def test_minorail_combo_after_2_normalizes_to_combo_1(self) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.I, lines=4, combo_after=2)
        )

        self.assertEqual(attack, 5)

    def test_minorail_back_to_back_after_1_has_no_repeated_back_to_back_bonus(
        self,
    ) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.I, lines=4, back_to_back_after=1)
        )

        self.assertEqual(attack, 4)

    def test_minorail_back_to_back_after_2_has_repeated_back_to_back_bonus(
        self,
    ) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.I, lines=4, back_to_back_after=2)
        )

        self.assertEqual(attack, 5)

    def test_high_combo_back_to_back_tetris_uses_normalized_counters(self) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.I, lines=4, combo_after=16, back_to_back_after=2)
        )

        self.assertEqual(attack, 23)

    def test_perfect_clear_tetris_uses_s2_special_bonus(self) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(
                Piece.I,
                lines=4,
                perfect_clear=True,
                combo_after=1,
                back_to_back_after=2,
            )
        )

        self.assertEqual(attack, 11)

    def test_back_to_back_surge_uses_normalized_back_to_back_before_counter(
        self,
    ) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(
                Piece.I,
                lines=1,
                back_to_back_before=9,
                back_to_back_after=0,
            )
        )

        self.assertEqual(attack, 7)

    def test_non_t_spin_double_is_not_treated_as_full_t_spin_attack(self) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.L, lines=2, spin=Spin.full)
        )

        self.assertEqual(attack, 1)

    def test_t_spin_double_still_uses_t_spin_attack(self) -> None:
        attack = TetrioS2AttackCalculator().calculate(
            _applied(Piece.T, lines=2, spin=Spin.full)
        )

        self.assertEqual(attack, 4)


class TetrioS1AttackCalculatorTests(unittest.TestCase):
    def test_perfect_clear_is_10_without_s2_special_bonus(self) -> None:
        attack = TetrioS1AttackCalculator().calculate(
            _applied(Piece.I, lines=4, perfect_clear=True, back_to_back_after=2)
        )

        self.assertEqual(attack, 15)

    def test_back_to_back_chaining_uses_normalized_back_to_back(self) -> None:
        attack = TetrioS1AttackCalculator().calculate(
            _applied(Piece.I, lines=4, back_to_back_after=4)
        )

        self.assertEqual(attack, 6)


class GuidelineAttackCalculatorTests(unittest.TestCase):
    def test_classic_guideline_uses_fixed_additive_combo_table(self) -> None:
        attack = ClassicGuidelineAttackCalculator().calculate(
            _applied(Piece.I, lines=4, combo_after=6)
        )

        self.assertEqual(attack, 7)

    def test_modern_guideline_uses_fixed_additive_combo_table(self) -> None:
        attack = ModernGuidelineAttackCalculator().calculate(
            _applied(Piece.I, lines=4, combo_after=6)
        )

        self.assertEqual(attack, 6)


class PptAttackCalculatorTests(unittest.TestCase):
    def test_t_spin_double_uses_adjusted_ppt_attack(self) -> None:
        attack = PptAttackCalculator().calculate(
            _applied(Piece.T, lines=2, spin=Spin.full)
        )

        self.assertEqual(attack, 3)

    def test_t_spin_triple_matches_tetris_attack(self) -> None:
        attack = PptAttackCalculator().calculate(
            _applied(Piece.T, lines=3, spin=Spin.full)
        )

        self.assertEqual(attack, 4)

    def test_perfect_clear_uses_adjusted_ppt_bonus(self) -> None:
        attack = PptAttackCalculator().calculate(
            _applied(Piece.I, lines=4, perfect_clear=True)
        )

        self.assertEqual(attack, 10)

    def test_back_to_back_t_spin_double_adds_one(self) -> None:
        attack = PptAttackCalculator().calculate(
            _applied(Piece.T, lines=2, spin=Spin.full, back_to_back_after=2)
        )

        self.assertEqual(attack, 4)

    def test_short_combo_uses_adjusted_ppt_bonus(self) -> None:
        attack = PptAttackCalculator().calculate(
            _applied(Piece.I, lines=4, combo_after=5)
        )

        self.assertEqual(attack, 5)


def _applied(
    piece: Piece,
    *,
    lines: int,
    spin: Spin = Spin.none,
    perfect_clear: bool = False,
    combo_after: int = 1,
    back_to_back_before: int = 0,
    back_to_back_after: int = 0,
) -> AppliedMove:
    return AppliedMove(
        placement=Placement(PieceLocation(piece, Rotation.North, 4, 0), spin),
        lines_cleared=lines,
        perfect_clear=perfect_clear,
        combo_before=max(0, combo_after - 1),
        combo_after=combo_after,
        back_to_back_before=back_to_back_before,
        back_to_back_after=back_to_back_after,
    )


if __name__ == "__main__":
    unittest.main()
