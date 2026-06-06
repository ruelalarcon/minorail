from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.board import Board
from core.piece import Piece
from core.placement import Placement


@dataclass
class MsgRules:
    randomizer: Optional[str] = None


@dataclass
class MsgStart:
    board: Board
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: bool
    randomizer: dict[str, Any] = field(default_factory=dict)


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
