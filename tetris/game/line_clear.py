from __future__ import annotations

from dataclasses import dataclass

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rules import Rules
from tetris.model.spin import Spin


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
        all_clear = board.is_empty()
        hard = (
            cleared.bit_count() == 4
            or (spin != Spin.none and (piece == Piece.T or rules.allspin_b2b))
            or (rules.allclear_b2b and all_clear)
        )
        return LineClearResult(
            lines_cleared=cleared.bit_count(),
            perfect_clear=all_clear,
            combo=combo + 1,
            back_to_back=back_to_back + 1 if hard else 0,
        )
