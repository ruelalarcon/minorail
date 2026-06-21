from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells


@dataclass
class Board:
    """Column-major bitboard: cols[x] has bit y set iff (x, y) is occupied."""

    cols: list[int] = field(default_factory=lambda: [0] * 10)
    height: int = 40

    def __post_init__(self) -> None:
        if len(self.cols) < 1:
            raise ValueError("board must have at least 1 column")
        if self.height < 1:
            raise ValueError("board height must be at least 1")
        limit = 1 << self.height
        for i, col in enumerate(self.cols):
            if col < 0 or col >= limit:
                raise ValueError(f"board column {i} must fit in {self.height} bits")

    @property
    def width(self) -> int:
        return len(self.cols)

    @staticmethod
    def empty(width: int = 10, height: int = 40) -> Board:
        return Board(cols=[0] * width, height=height)

    @staticmethod
    def from_sbp(
        rows: list[list[Optional[str]]],
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> Board:
        """Parse SBP board rows, where row 0 is the bottom."""
        parsed_height = 40 if height is None else height
        parsed_width = (
            max((len(row) for row in rows), default=10) if width is None else width
        )
        cols = [0] * parsed_width
        for y, row in enumerate(rows):
            if y >= parsed_height:
                break
            for x, cell in enumerate(row):
                if x < parsed_width and cell is not None:
                    cols[x] |= 1 << y
        return Board(cols=cols, height=parsed_height)

    def occupied(self, x: int, y: int) -> bool:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return bool(self.cols[x] & (1 << y))

    def place(self, piece: Piece, rotation: Rotation, cx: int, cy: int) -> None:
        for x, y in piece_cells(piece, rotation, cx, cy):
            assert 0 <= x < self.width and 0 <= y < self.height
            self.cols[x] |= 1 << y

    def line_clears(self) -> int:
        """Bitmask of completely filled rows."""
        mask = (1 << self.height) - 1
        for c in self.cols:
            mask &= c
        return mask

    def remove_lines(self, lines: int) -> None:
        """Clear rows indicated by bitmask, shifting rows above down."""
        for i in range(self.width):
            self.cols[i] = _clear_lines(self.cols[i], lines, self.height)

    def distance_to_ground(self, x: int, y: int) -> int:
        """How many rows cell (x, y) can fall before hitting something."""
        assert 0 <= x < self.width and 0 <= y < self.height
        blockers_below = self.cols[x] & ((1 << y) - 1)
        if blockers_below == 0:
            return y
        highest_blocker_y = blockers_below.bit_length() - 1
        return y - highest_blocker_y - 1

    def drop_distance(self, piece: Piece, rotation: Rotation, cx: int, cy: int) -> int:
        """How far the piece can drop from (cx, cy) before landing."""
        result = self.height
        for x, y in piece_cells(piece, rotation, cx, cy):
            if x < 0 or x >= self.width:
                continue
            if y < 0:
                return 0
            if y >= self.height:
                continue
            result = min(result, self.distance_to_ground(x, y))
        return result

    def is_empty(self) -> bool:
        return all(c == 0 for c in self.cols)

    def copy(self) -> Board:
        return Board(cols=list(self.cols), height=self.height)


def _clear_lines(col: int, lines: int, height: int) -> int:
    """Remove rows in `lines` bitmask from col, shifting higher bits down."""
    mask = (1 << height) - 1
    col &= mask
    remaining = lines & mask
    while remaining:
        i = (remaining & -remaining).bit_length() - 1
        low_mask = (1 << i) - 1
        col = (col & low_mask) | ((col >> 1) & ~low_mask & mask)
        remaining &= ~(1 << i)
        remaining >>= 1
    return col
