from __future__ import annotations

from battle.attack.base import AttackResult
from tetris.game.state import AppliedMove
from tetris.model.piece import Piece
from tetris.model.spin import Spin


class GenericAttackCalculator:
    LINE_CLEAR_ATTACK = {
        0: 0,
        1: 0,
        2: 1,
        3: 2,
        4: 4,
    }
    T_SPIN_ATTACK = {
        1: 2,
        2: 4,
        3: 6,
    }
    PERFECT_CLEAR_BONUS = 10
    COMBO_BONUS_PER_STEP = 1
    BACK_TO_BACK_BONUS = 1
    BACK_TO_BACK_MIN = 2

    def calculate(self, applied: AppliedMove) -> AttackResult:
        line_clear = self._line_clear_attack(applied)
        combo = self._combo_bonus(applied)
        back_to_back = self._back_to_back_bonus(applied)
        perfect_clear = self.PERFECT_CLEAR_BONUS if applied.perfect_clear else 0
        breakdown = {
            "line_clear": line_clear,
            "combo": combo,
            "back_to_back": back_to_back,
            "perfect_clear": perfect_clear,
        }
        return AttackResult(attack=sum(breakdown.values()), breakdown=breakdown)

    def _line_clear_attack(self, applied: AppliedMove) -> int:
        lines = applied.lines_cleared
        if (
            applied.placement.location.piece == Piece.T
            and applied.placement.spin != Spin.none
        ):
            return self.T_SPIN_ATTACK.get(lines, 0)
        return self.LINE_CLEAR_ATTACK.get(lines, 0)

    def _combo_bonus(self, applied: AppliedMove) -> int:
        if applied.lines_cleared == 0:
            return 0
        return max(0, applied.combo_after - 1) * self.COMBO_BONUS_PER_STEP

    def _back_to_back_bonus(self, applied: AppliedMove) -> int:
        if applied.lines_cleared == 0:
            return 0
        if applied.back_to_back_after < self.BACK_TO_BACK_MIN:
            return 0
        return self.BACK_TO_BACK_BONUS
