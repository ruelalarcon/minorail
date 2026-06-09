from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells


@dataclass
class PieceLocation:
    piece: Piece
    rotation: Rotation
    x: int
    y: int

    def cells(self) -> tuple[tuple[int, int], ...]:
        return piece_cells(self.piece, self.rotation, self.x, self.y)

    def to_tbp(self) -> dict[str, Any]:
        return {
            "type": self.piece.value,
            "orientation": self.rotation.value,
            "x": self.x,
            "y": self.y,
        }

    @staticmethod
    def from_tbp(d: dict[str, Any]) -> PieceLocation:
        return PieceLocation(
            piece=Piece(d["type"]),
            rotation=Rotation(d["orientation"]),
            x=d["x"],
            y=d["y"],
        )
