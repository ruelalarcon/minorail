from __future__ import annotations

import math

from battle.attack.common import (
    normalized_b2b,
    normalized_b2b_before,
    normalized_combo,
    t_spin_only_line_clear_attack,
)
from tetris.game.state import AppliedMove
from tetris.model.piece import Piece
from tetris.model.spin import Spin


class TetrioS2AttackCalculator:
    PERFECT_CLEAR_BONUS = 5
    BACK_TO_BACK_BONUS = 1
    B2B_SURGE_AT = 4
    B2B_SURGE_BASE = 3

    def calculate(self, applied: AppliedMove) -> int:
        # Minorail counters are one-based from the first clear. TETR.IO combo
        # and B2B attack formulas use displayed/derived counts, so subtract one.
        combo = normalized_combo(applied)
        b2b = normalized_b2b(applied)
        b2b_before = normalized_b2b_before(applied)

        line_clear = t_spin_only_line_clear_attack(applied)
        back_to_back = (
            self.BACK_TO_BACK_BONUS if applied.lines_cleared > 0 and b2b > 0 else 0
        )
        special_bonus = (
            1
            if applied.perfect_clear
            and (applied.lines_cleared == 4 or _is_t_piece_spin_clear(applied))
            else 0
        )
        surge = self._b2b_surge(applied, b2b_before)

        subtotal = line_clear + back_to_back + special_bonus
        line_attack = _attack_round(_multiplier_combo_attack(subtotal, combo))
        perfect_clear = self.PERFECT_CLEAR_BONUS if applied.perfect_clear else 0
        return line_attack + perfect_clear + surge

    def _b2b_surge(self, applied: AppliedMove, b2b_before: int) -> int:
        if (
            applied.lines_cleared > 0
            and applied.back_to_back_after == 0
            and b2b_before > self.B2B_SURGE_AT
        ):
            return math.floor(b2b_before - self.B2B_SURGE_AT + self.B2B_SURGE_BASE)
        return 0


def _attack_round(attack: float) -> int:
    return math.floor(attack)


def _multiplier_combo_attack(attack: float, combo: int) -> float:
    if combo <= 0:
        return attack
    attack *= 1 + 0.25 * combo
    if combo > 1:
        attack = max(math.log1p(combo * 1.25), attack)
    return attack


def _is_t_piece_spin_clear(applied: AppliedMove) -> bool:
    return (
        applied.lines_cleared > 0
        and applied.placement.location.piece == Piece.T
        and applied.placement.spin != Spin.none
    )
