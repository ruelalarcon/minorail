from __future__ import annotations

from dataclasses import dataclass

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.game.back_to_back import is_back_to_back_clear


@dataclass(frozen=True)
class LineClearResult:
    lines_cleared: int
    perfect_clear: bool
    combo: int
    back_to_back: int


class LineClear:
    @staticmethod
    def apply(
        board: Board,
        *,
        combo: int,
        back_to_back: int,
        piece: Piece,
        spin: Spin,
        rules: Rules,
    ) -> LineClearResult:
        cleared = board.line_clears()
        if not cleared:
            return LineClearResult(
                lines_cleared=0,
                perfect_clear=False,
                combo=0,
                back_to_back=back_to_back,
            )

        board.remove_lines(cleared)
        perfect_clear = board.is_empty()
        lines_cleared = cleared.bit_count()
        hard = is_back_to_back_clear(
            piece,
            spin,
            lines_cleared,
            perfect_clear,
            rules,
        )
        return LineClearResult(
            lines_cleared=lines_cleared,
            perfect_clear=perfect_clear,
            combo=combo + 1,
            back_to_back=back_to_back + 1 if hard else 0,
        )
