from __future__ import annotations

from tetris.model.piece import Piece
from tetris.model.rotation import Rotation, rotate_cell

RelativeCells = tuple[tuple[int, int], ...]

_NORTH_CELLS: dict[Piece, RelativeCells] = {
    Piece.I: ((-1, 0), (0, 0), (1, 0), (2, 0)),
    Piece.J: ((-1, 0), (0, 0), (1, 0), (-1, 1)),
    Piece.L: ((-1, 0), (0, 0), (1, 0), (1, 1)),
    Piece.O: ((0, 0), (1, 0), (0, 1), (1, 1)),
    Piece.S: ((-1, 0), (0, 0), (0, 1), (1, 1)),
    Piece.T: ((-1, 0), (0, 0), (1, 0), (0, 1)),
    Piece.Z: ((-1, 1), (0, 1), (0, 0), (1, 0)),
}

_PIECE_CELLS: dict[Piece, dict[Rotation, RelativeCells]] = {
    piece: {
        rotation: tuple(rotate_cell(rotation, x, y) for x, y in cells)
        for rotation in Rotation
    }
    for piece, cells in _NORTH_CELLS.items()
}


def relative_piece_cells(piece: Piece, rotation: Rotation) -> RelativeCells:
    return _PIECE_CELLS[piece][rotation]


def piece_cells(
    piece: Piece, rotation: Rotation, cx: int, cy: int
) -> tuple[tuple[int, int], ...]:
    """Return absolute board coordinates of all cells for a piece at (cx, cy)."""
    return tuple((cx + dx, cy + dy) for dx, dy in relative_piece_cells(piece, rotation))
