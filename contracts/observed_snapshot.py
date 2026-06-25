from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement


@dataclass
class ObservedSnapshot:
    board: Board
    active: PieceLocation
    queue: list[Piece]
    hold: Optional[Piece]
    can_hold: bool
    seq: int
    last_move: Optional[Placement] = None

    def copy(self) -> ObservedSnapshot:
        return ObservedSnapshot(
            board=self.board.copy(),
            active=self.active,
            queue=list(self.queue),
            hold=self.hold,
            can_hold=self.can_hold,
            seq=self.seq,
            last_move=self.last_move,
        )

    def physically_equals(self, other: ObservedSnapshot) -> bool:
        return (
            self.board.rows == other.board.rows
            and self.active == other.active
            and self.queue == other.queue
            and self.hold == other.hold
            and self.can_hold == other.can_hold
        )
