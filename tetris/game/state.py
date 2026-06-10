from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Optional

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.pieces.cells import piece_cells
from tetris.pieces import spawn as _spawn
from tetris.game.hold import Hold
from tetris.game.line_clear import LineClear

if TYPE_CHECKING:
    from protocols.sbp.messages import MsgStart

_ALL_PIECES = list(Piece)
SPAWN_X = _spawn.SPAWN_X
SPAWN_Y = _spawn.SPAWN_Y
spawn_location = _spawn.spawn_location


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
        """Build initial state from an SBP start message."""
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
        hold_result = Hold.infer_after_placement(
            active=self.active.piece,
            hold=self.hold,
            queue=self.queue,
            placement=placement,
            hold_used_this_turn=self.hold_used_this_turn,
        )
        if hold_result is None:
            return False

        if not hold_result.queue:
            return False
        rules = rules or Rules()
        next_queue = list(hold_result.queue)
        next_active = spawn_location(
            next_queue.pop(0), x=rules.spawn_x, y=rules.spawn_y
        )

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
        self.hold = hold_result.hold

        clear_result = LineClear.apply(
            self.board,
            combo=self.combo,
            back_to_back=self.back_to_back,
            spin=placement.spin,
            rules=rules,
        )
        self.combo = clear_result.combo
        self.back_to_back = clear_result.back_to_back

        self.hold_used_this_turn = False
        return True
