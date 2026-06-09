from __future__ import annotations

from dataclasses import dataclass

from tetris.model.board import Board
from tetris.model.rules import Rules
from tetris.model.spin import Spin


@dataclass(frozen=True)
class LineClearResult:
    combo: int
    back_to_back: int


class LineClear:
    @staticmethod
    def apply(
        board: Board,
        *,
        combo: int,
        back_to_back: int,
        spin: Spin,
        rules: Rules,
    ) -> LineClearResult:
        cleared = board.line_clears()
        if not cleared:
            return LineClearResult(combo=0, back_to_back=back_to_back)

        board.remove_lines(cleared)
        all_clear = board.is_empty()
        hard = (
            cleared.bit_count() == 4
            or (rules.allspin_b2b and spin != Spin.none)
            or (rules.allclear_b2b and all_clear)
        )
        return LineClearResult(
            combo=combo + 1,
            back_to_back=back_to_back + 1 if hard else 0,
        )
