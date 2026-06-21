from __future__ import annotations

import math

from battle.attack.common import (
    normalized_back_to_back,
    normalized_combo,
    t_spin_only_line_clear_attack,
)
from tetris.game.state import AppliedMove


class TetrioS1AttackCalculator:
    PERFECT_CLEAR_BONUS = 10

    def calculate(self, applied: AppliedMove) -> int:
        # Minorail counters are one-based from the first clear. TETR.IO combo
        # and back-to-back attack formulas use displayed/derived counts, so subtract one.
        combo = normalized_combo(applied)
        back_to_back = normalized_back_to_back(applied)

        line_clear = t_spin_only_line_clear_attack(applied)
        back_to_back = _back_to_back_chaining_bonus(back_to_back)
        subtotal = line_clear + back_to_back
        multiplied = _multiplier_combo_attack(subtotal, combo)
        line_attack = _attack_round(multiplied)
        perfect_clear = self.PERFECT_CLEAR_BONUS if applied.perfect_clear else 0
        return line_attack + perfect_clear


def _attack_round(attack: float) -> int:
    return math.floor(attack)


def _multiplier_combo_attack(attack: float, combo: int) -> float:
    if combo <= 0:
        return attack
    attack *= 1 + 0.25 * combo
    if combo > 1:
        attack = max(math.log1p(combo * 1.25), attack)
    return attack


def _back_to_back_chaining_bonus(back_to_back: int) -> float:
    if back_to_back <= 0:
        return 0
    raw = 1 + math.log1p(back_to_back * 0.8)
    bonus = math.floor(raw)
    if back_to_back != 1:
        bonus += (raw % 1) / 3
    return bonus
