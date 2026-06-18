from dataclasses import dataclass

from tetris.model.piece import Piece


@dataclass
class PieceStreamSnapshot:
    offset: int | None
    pieces: list[Piece]
