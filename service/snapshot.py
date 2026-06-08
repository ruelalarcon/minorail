from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.board import Board
from core.piece import Piece
from core.placement import Placement
from game.rules import Rules
from movegen.pathfinder import MoveStep


@dataclass
class ObservedSnapshot:
    board: Board
    current: Optional[Piece]
    queue: list[Piece]
    hold: Optional[Piece]
    can_hold: bool
    seq: int
    last_move: Optional[Placement] = None

    def copy(self) -> ObservedSnapshot:
        return ObservedSnapshot(
            board=self.board.copy(),
            current=self.current,
            queue=list(self.queue),
            hold=self.hold,
            can_hold=self.can_hold,
            seq=self.seq,
            last_move=self.last_move,
        )

    def physically_equals(self, other: ObservedSnapshot) -> bool:
        return (
            self.board.cols == other.board.cols
            and self.current == other.current
            and self.queue == other.queue
            and self.hold == other.hold
            and self.can_hold == other.can_hold
        )


@dataclass
class PieceStreamSnapshot:
    offset: int | None
    pieces: list[Piece]


@dataclass
class BotSnapshot:
    board: Board
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    piece_stream: Optional[PieceStreamSnapshot] = None


@dataclass
class SuggestionRequest:
    snapshot: ObservedSnapshot
    rules: Rules
    include_path: bool = True
    session_id: str = "default"
    timeout_ms: int = 10_000


class SuggestionStatus(Enum):
    Synced = "synced"
    Advanced = "advanced"
    Resynced = "resynced"
    Invalid = "invalid"
    NoSuggestion = "no_suggestion"


@dataclass
class SuggestionResult:
    seq: int
    status: SuggestionStatus
    placements: list[Placement]
    placement: Optional[Placement]
    path: Optional[list[MoveStep]]
    reason: Optional[str] = None
