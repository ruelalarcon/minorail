from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.board import Board, piece_cells
from core.piece import Piece
from core.placement import Placement
from core.spin import Spin
from tbp.messages import MsgStart

_ALL_PIECES = list(Piece)


@dataclass
class GameState:
    board: Board
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: bool
    hold_used_this_turn: bool = False

    @staticmethod
    def from_start(msg: MsgStart) -> GameState:
        """Build initial state from a TBP start message."""
        return GameState(
            board=msg.board.copy(),
            queue=list(msg.queue),
            hold=msg.hold,
            combo=msg.combo,
            back_to_back=msg.back_to_back,
        )

    def current_piece(self) -> Optional[Piece]:
        return self.queue[0] if self.queue else None

    def apply_move(self, placement: Placement) -> bool:
        """
        Apply a bot move. Returns False if the move is illegal.
        Hold is inferred from the placed piece type vs queue front.
        """
        if not self.queue:
            return False

        placed = placement.location.piece
        front = self.queue[0]

        if placed == front:
            self.queue.pop(0)
        elif self.hold is None:
            if len(self.queue) < 2 or placed != self.queue[1]:
                return False
            self.hold = self.queue.pop(0)
            self.queue.pop(0)
        else:
            if placed != self.hold:
                return False
            self.hold, self.queue[0] = self.queue[0], self.hold
            self.queue.pop(0)

        loc = placement.location
        cells = piece_cells(loc.piece, loc.rotation, loc.x, loc.y)
        for x, y in cells:
            if x < 0 or x >= 10 or y < 0 or y >= 40:
                return False
            if self.board.occupied(x, y):
                return False

        self.board.place(loc.piece, loc.rotation, loc.x, loc.y)

        cleared = self.board.line_clears()
        if cleared:
            self.board.remove_lines(cleared)
            hard = bin(cleared).count("1") == 4 or placement.spin != Spin.none
            self.back_to_back = hard
            self.combo += 1
        else:
            self.combo = 0

        self.hold_used_this_turn = False
        return True
