from __future__ import annotations

from tetris.game.state import AppliedMove
from tetris.model.piece import Piece
from tetris.model.spin import Spin

BASE_LINE_CLEAR_ATTACK = {
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
    4: 10,
    5: 12,
}

T_SPIN_MINI_ATTACK = {
    1: 0,
    2: 1,
    3: 2,
    4: 4,
}


def normalized_combo(applied: AppliedMove) -> int:
    return max(0, applied.combo_after - 1)


def normalized_back_to_back(applied: AppliedMove) -> int:
    return max(0, applied.back_to_back_after - 1)


def normalized_back_to_back_before(applied: AppliedMove) -> int:
    return max(0, applied.back_to_back_before - 1)


def fixed_combo_bonus(combo_table: list[int], normalized_combo: int) -> int:
    if normalized_combo <= 0:
        return 0
    return combo_table[min(normalized_combo, len(combo_table) - 1)]


def t_spin_only_line_clear_attack(applied: AppliedMove) -> int:
    lines = applied.lines_cleared
    if applied.placement.location.piece != Piece.T:
        return BASE_LINE_CLEAR_ATTACK.get(lines, 0)
    if applied.placement.spin == Spin.full:
        return T_SPIN_ATTACK.get(lines, 0)
    if applied.placement.spin == Spin.mini:
        return T_SPIN_MINI_ATTACK.get(lines, 0)
    return BASE_LINE_CLEAR_ATTACK.get(lines, 0)
