from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.board import Board, piece_cells
from core.location import PieceLocation
from core.piece import Piece
from core.placement import Placement
from core.rotation import Rotation
from core.spin import Spin
from game.rules import Rules
from tbp.messages import MsgStart

_ALL_PIECES = list(Piece)
SPAWN_X = 4
SPAWN_Y = 19


@dataclass
class GameState:
    board: Board
    active: PieceLocation
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    hold_used_this_turn: bool = False

    @staticmethod
    def from_start(msg: MsgStart) -> GameState:
        """Build initial state from a TBP start message."""
        return GameState(
            board=msg.board.copy(),
            active=spawn_location(msg.active),
            queue=list(msg.queue),
            hold=msg.hold,
            combo=msg.combo,
            back_to_back=msg.back_to_back,
        )

    def active_piece(self) -> Piece:
        return self.active.piece

    def apply_move(self, placement: Placement, rules: Rules | None = None) -> bool:
        """
        Apply a bot move. Returns False if the move is illegal.
        Hold is inferred from the placed piece type vs active and hold state.
        """
        placed = placement.location.piece
        next_hold = self.hold
        next_queue = list(self.queue)
        if placed == self.active.piece:
            pass
        elif not self.hold_used_this_turn and self.hold is None:
            if not next_queue or placed != next_queue[0]:
                return False
            next_hold = self.active.piece
            next_queue.pop(0)
        elif not self.hold_used_this_turn and placed == self.hold:
            next_hold = self.active.piece
        else:
            return False

        if not next_queue:
            return False
        next_active = spawn_location(next_queue.pop(0))

        loc = placement.location
        cells = piece_cells(loc.piece, loc.rotation, loc.x, loc.y)
        for x, y in cells:
            if x < 0 or x >= 10 or y < 0 or y >= 40:
                return False
            if self.board.occupied(x, y):
                return False

        self.board.place(loc.piece, loc.rotation, loc.x, loc.y)
        self.active = next_active
        self.queue = next_queue
        self.hold = next_hold

        cleared = self.board.line_clears()
        if cleared:
            self.board.remove_lines(cleared)
            active_rules = rules or Rules()
            all_clear = all(c == 0 for c in self.board.cols)
            hard = (
                bin(cleared).count("1") == 4
                or (active_rules.allspin_b2b and placement.spin != Spin.none)
                or (active_rules.allclear_b2b and all_clear)
            )
            self.back_to_back = self.back_to_back + 1 if hard else 0
            self.combo += 1
        else:
            self.combo = 0

        self.hold_used_this_turn = False
        return True


def spawn_location(piece: Piece) -> PieceLocation:
    return PieceLocation(piece, Rotation.North, SPAWN_X, SPAWN_Y)
