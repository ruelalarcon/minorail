from __future__ import annotations

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.movegen.collision import obstructed


def immobile(location: PieceLocation, board: Board) -> bool:
    return all(
        obstructed(
            board,
            location.piece,
            location.rotation,
            location.x + dx,
            location.y + dy,
        )
        for dx, dy in ((-1, 0), (1, 0), (0, 1))
    )
