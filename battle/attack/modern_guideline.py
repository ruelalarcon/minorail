from __future__ import annotations

from battle.attack.common import (
    fixed_combo_bonus,
    normalized_b2b,
    normalized_combo,
    t_spin_only_line_clear_attack,
)
from tetris.game.state import AppliedMove


class ModernGuidelineAttackCalculator:
    COMBO_TABLE = [0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4]
    PERFECT_CLEAR_BONUS = 10
    BACK_TO_BACK_BONUS = 1

    def calculate(self, applied: AppliedMove) -> int:
        # Minorail counters are one-based from the first clear. Guideline-style
        # combo and B2B formulas use displayed/derived counts, so subtract one.
        combo = normalized_combo(applied)
        b2b = normalized_b2b(applied)

        line_clear = t_spin_only_line_clear_attack(applied)
        back_to_back = (
            self.BACK_TO_BACK_BONUS if applied.lines_cleared > 0 and b2b > 0 else 0
        )
        combo_bonus = fixed_combo_bonus(self.COMBO_TABLE, combo)
        perfect_clear = self.PERFECT_CLEAR_BONUS if applied.perfect_clear else 0
        return line_clear + back_to_back + combo_bonus + perfect_clear
