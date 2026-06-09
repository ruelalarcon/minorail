from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tetris.model.board import Board
from tetris.model.piece import Piece
from suggestion.contracts.piece_stream_snapshot import PieceStreamSnapshot


@dataclass
class BotSnapshot:
    board: Board
    active: Piece
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    piece_stream: Optional[PieceStreamSnapshot] = None
