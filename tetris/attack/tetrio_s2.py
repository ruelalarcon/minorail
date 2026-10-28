from __future__ import annotations

import math

from tetris.attack.common import (
    normalized_back_to_back,
    normalized_combo,
    BASE_LINE_CLEAR_ATTACK,
    T_SPIN_ATTACK,
    T_SPIN_MINI_ATTACK,
)
from tetris.game.state import AppliedMove
from tetris.model.spin import Spin


class TetrioS2AttackCalculator:
    MODEL_VERSION = "tetrio-s2-packets-v3"
    PERFECT_CLEAR_BONUS = 5
    BACK_TO_BACK_BONUS = 1
    BACK_TO_BACK_SURGE_AT = 4
    BACK_TO_BACK_SURGE_BASE = 3

    def packets(self, applied: AppliedMove) -> tuple[int, ...]:
        if applied.lines_cleared <= 0:
            return ()

        # Combo multiplication and the repeated-B2B bonus use displayed counts.
        combo = normalized_combo(applied)
        back_to_back = normalized_back_to_back(applied)
        # The client uses the raw one-based stats.btb for charging; only the
        # ordinary repeated-B2B bonus uses the displayed counter.
        back_to_back_before = applied.back_to_back_before

        table = {
            Spin.none: BASE_LINE_CLEAR_ATTACK,
            Spin.mini: T_SPIN_MINI_ATTACK,
            Spin.full: T_SPIN_ATTACK,
        }[applied.placement.spin]
        line_clear = table.get(applied.lines_cleared, 0)
        back_to_back = (
            self.BACK_TO_BACK_BONUS
            if applied.lines_cleared > 0 and back_to_back > 0
            else 0
        )
        special_bonus = (
            1
            if applied.garbage_lines_cleared > 0
            and (applied.lines_cleared == 4 or applied.placement.spin != Spin.none)
            else 0
        )
        surge = self._back_to_back_surge(applied, back_to_back_before)

        subtotal = line_clear + back_to_back
        line_attack = _attack_round(_multiplier_combo_attack(subtotal, combo))
        perfect_clear = self.PERFECT_CLEAR_BONUS if applied.perfect_clear else 0
        # The client offsets/emits surge segments before the ordinary clear,
        # and sends the perfect-clear bonus in a separate final call.
        third = (surge + 1) // 3  # Math.round(integer_surge / 3)
        return tuple(
            packet
            for packet in (
                third,
                third,
                surge - 2 * third,
                line_attack + special_bonus,
                perfect_clear,
            )
            if packet > 0
        )

    def _back_to_back_surge(
        self, applied: AppliedMove, back_to_back_before: int
    ) -> int:
        if (
            applied.lines_cleared > 0
            and applied.back_to_back_after == 0
            and back_to_back_before > self.BACK_TO_BACK_SURGE_AT
        ):
            return math.floor(
                back_to_back_before
                - self.BACK_TO_BACK_SURGE_AT
                + self.BACK_TO_BACK_SURGE_BASE
            )
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
