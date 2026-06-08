from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from core.board import Board
from core.piece import Piece
from core.placement import Placement

if TYPE_CHECKING:
    from service.snapshot import PieceStreamSnapshot


@dataclass
class MsgRules:
    randomizer: Optional[str] = None
    kickset: Optional[str] = None
    rot180: Optional[bool] = None
    sonic_drop: Optional[str] = None
    allspin_b2b: Optional[bool] = None
    allclear_b2b: Optional[bool] = None


@dataclass
class MsgStart:
    board: Board
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    piece_stream: Optional["PieceStreamSnapshot"] = None


@dataclass
class MsgPlay:
    move: Placement


@dataclass
class MsgNewPiece:
    piece: Piece


@dataclass
class MsgSuggest:
    pass


@dataclass
class MsgStop:
    pass


@dataclass
class MsgQuit:
    pass
