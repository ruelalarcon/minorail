from __future__ import annotations

from tetris.attack.common import (
    BASE_LINE_CLEAR_ATTACK,
    T_SPIN_MINI_ATTACK,
    fixed_combo_bonus,
    normalized_back_to_back,
    normalized_combo,
)
from tetris.game.state import AppliedMove
from tetris.model.piece import Piece
from tetris.model.spin import Spin


class PptAttackCalculator:
    """Puyo Puyo Tetris-style attack based on public community notes.

    FOUR.lol documents the adjusted PPT Tetris-vs-Puyo attack gauge: T-Spin
    Double 3, T-Spin Triple 4, perfect-clear 6, back-to-back +1, and a weakened combo
    table. This is not an official Sega/Tetris Guideline specification.
    """

    COMBO_TABLE = [0, 0, 1, 1, 1, 1, 1, 2]
    PERFECT_CLEAR_BONUS = 6
    BACK_TO_BACK_BONUS = 1
    T_SPIN_ATTACK = {
        1: 2,
        2: 3,
        3: 4,
    }

    def calculate(self, applied: AppliedMove) -> int:
        combo = normalized_combo(applied)
        back_to_back = normalized_back_to_back(applied)

        line_clear = self._line_clear_attack(applied)
        back_to_back = (
            self.BACK_TO_BACK_BONUS
            if applied.lines_cleared > 0 and back_to_back > 0
            else 0
        )
        combo_bonus = fixed_combo_bonus(self.COMBO_TABLE, combo)
        perfect_clear = self.PERFECT_CLEAR_BONUS if applied.perfect_clear else 0
        return line_clear + back_to_back + combo_bonus + perfect_clear

    def _line_clear_attack(self, applied: AppliedMove) -> int:
        lines = applied.lines_cleared
        if applied.placement.location.piece != Piece.T:
            return BASE_LINE_CLEAR_ATTACK.get(lines, 0)
        if applied.placement.spin == Spin.full:
            return self.T_SPIN_ATTACK.get(lines, 0)
        if applied.placement.spin == Spin.mini:
            return T_SPIN_MINI_ATTACK.get(lines, 0)
        return BASE_LINE_CLEAR_ATTACK.get(lines, 0)
