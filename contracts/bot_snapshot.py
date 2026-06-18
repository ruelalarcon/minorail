from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from contracts.piece_stream_snapshot import PieceStreamSnapshot
from tetris.model.board import Board
from tetris.model.piece import Piece


@dataclass
class BotSnapshot:
    board: Board
    active: Piece
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    piece_stream: Optional[PieceStreamSnapshot] = None
    extensions: dict[str, Any] | None = None
