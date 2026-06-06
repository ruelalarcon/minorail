from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.piece import Piece
from core.rotation import Rotation, rotate_cell

# North-orientation cell offsets per piece, relative to SRS center.
_PIECE_CELLS: dict[Piece, list[tuple[int, int]]] = {
    Piece.I: [(-1, 0), (0, 0), (1, 0), (2, 0)],
    Piece.O: [(0, 0), (1, 0), (0, 1), (1, 1)],
    Piece.T: [(-1, 0), (0, 0), (1, 0), (0, 1)],
    Piece.L: [(-1, 0), (0, 0), (1, 0), (1, 1)],
    Piece.J: [(-1, 0), (0, 0), (1, 0), (-1, 1)],
    Piece.S: [(-1, 0), (0, 0), (0, 1), (1, 1)],
    Piece.Z: [(-1, 1), (0, 1), (0, 0), (1, 0)],
}


def piece_cells(
    piece: Piece, rotation: Rotation, cx: int, cy: int
) -> list[tuple[int, int]]:
    """Return absolute board coordinates of all cells for a piece at (cx, cy)."""
    return [
        (cx + dx, cy + dy)
        for (dx, dy) in (rotate_cell(rotation, x, y) for x, y in _PIECE_CELLS[piece])
    ]


@dataclass
class Board:
    """Column-major bitboard: cols[x] has bit y set iff (x, y) is occupied."""

    cols: list[int] = field(default_factory=lambda: [0] * 10)

    @staticmethod
    def from_tbp(rows: list[list[Optional[str]]]) -> Board:
        """Parse TBP board: list of 40 rows (index 0 = bottom), each a list of
        10 cells (None = empty, any string = occupied)."""
        cols = [0] * 10
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell is not None:
                    cols[x] |= 1 << y
        return Board(cols=cols)

    def occupied(self, x: int, y: int) -> bool:
        if x < 0 or x >= 10 or y < 0 or y >= 40:
            return True
        return bool(self.cols[x] & (1 << y))

    def place(self, piece: Piece, rotation: Rotation, cx: int, cy: int) -> None:
        for x, y in piece_cells(piece, rotation, cx, cy):
            assert 0 <= x < 10 and 0 <= y < 40
            self.cols[x] |= 1 << y

    def line_clears(self) -> int:
        """Bitmask of completely filled rows."""
        mask = (1 << 40) - 1
        for c in self.cols:
            mask &= c
        return mask

    def remove_lines(self, lines: int) -> None:
        """Clear rows indicated by bitmask, shifting rows above down."""
        for i in range(10):
            self.cols[i] = _clear_lines(self.cols[i], lines)

    def distance_to_ground(self, x: int, y: int) -> int:
        """How many rows cell (x, y) can fall before hitting something."""
        assert 0 <= x < 10 and 0 <= y < 40
        if y == 0:
            return 0
        col = self.cols[x]
        inv = (~col) & ((1 << 40) - 1)
        shifted = (inv << (64 - y)) & 0xFFFFFFFFFFFFFFFF
        comp = (~shifted) & 0xFFFFFFFFFFFFFFFF
        return _leading_zeros_64(comp)

    def drop_distance(self, piece: Piece, rotation: Rotation, cx: int, cy: int) -> int:
        """How far the piece can drop from (cx, cy) before landing."""
        result = 40
        for x, y in piece_cells(piece, rotation, cx, cy):
            if x < 0 or x >= 10:
                continue
            if y < 0:
                return 0
            result = min(result, self.distance_to_ground(x, y))
        return result

    def is_empty(self) -> bool:
        return all(c == 0 for c in self.cols)

    def copy(self) -> Board:
        return Board(cols=list(self.cols))


def _leading_zeros_64(v: int) -> int:
    if v == 0:
        return 64
    n = 0
    if v & 0xFFFFFFFF00000000 == 0:
        n += 32
        v <<= 32
    if v & 0xFFFF000000000000 == 0:
        n += 16
        v <<= 16
    if v & 0xFF00000000000000 == 0:
        n += 8
        v <<= 8
    if v & 0xF000000000000000 == 0:
        n += 4
        v <<= 4
    if v & 0xC000000000000000 == 0:
        n += 2
        v <<= 2
    if v & 0x8000000000000000 == 0:
        n += 1
    return n


def _clear_lines(col: int, lines: int) -> int:
    """Remove rows in `lines` bitmask from col, shifting higher bits down."""
    mask40 = (1 << 40) - 1
    col &= mask40
    remaining = lines & mask40
    while remaining:
        i = (remaining & -remaining).bit_length() - 1
        low_mask = (1 << i) - 1
        col = (col & low_mask) | ((col >> 1) & ~low_mask & mask40)
        remaining &= ~(1 << i)
        remaining >>= 1
    return col
