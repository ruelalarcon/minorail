from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from tetris.model.piece import PIECES, Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells

EMPTY_CELL = 0
GARBAGE_CELL = 8
GENERIC_FILLED_CELL = GARBAGE_CELL

PIECE_TO_CELL = {piece: i + 1 for i, piece in enumerate(PIECES)}
CELL_TO_LABEL = {value: piece.value for piece, value in PIECE_TO_CELL.items()}
CELL_TO_LABEL[GARBAGE_CELL] = "G"
LABEL_TO_CELL = {label: value for value, label in CELL_TO_LABEL.items()}


@dataclass(init=False)
class Board:
    """Row-major byte board: rows[y][x] is 0 for empty, nonzero for occupied."""

    rows: list[bytearray] = field(default_factory=list)

    def __init__(
        self,
        cols: list[int] | None = None,
        *,
        rows: Sequence[bytearray | Sequence[int]] | None = None,
        height: int = 40,
    ) -> None:
        if rows is not None and cols is not None:
            raise ValueError("board cannot be initialized with both rows and cols")
        if rows is not None:
            self.rows = [_coerce_row(row) for row in rows]
            self._validate_rows()
            return
        if height < 1:
            raise ValueError("board height must be at least 1")
        source_cols = [0] * 10 if cols is None else list(cols)
        if len(source_cols) < 1:
            raise ValueError("board must have at least 1 column")
        limit = 1 << height
        for i, col in enumerate(source_cols):
            if col < 0 or col >= limit:
                raise ValueError(f"board column {i} must fit in {height} bits")
        self.rows = [bytearray(len(source_cols)) for _ in range(height)]
        for x, col in enumerate(source_cols):
            bits = col
            while bits:
                y = (bits & -bits).bit_length() - 1
                self.rows[y][x] = GENERIC_FILLED_CELL
                bits &= ~(1 << y)
        self._validate_rows()

    def _validate_rows(self) -> None:
        if len(self.rows) < 1:
            raise ValueError("board height must be at least 1")
        width = len(self.rows[0])
        if width < 1:
            raise ValueError("board must have at least 1 column")
        for y, row in enumerate(self.rows):
            if len(row) != width:
                raise ValueError(f"board row {y} must contain {width} cells")
            for value in row:
                if value < 0 or value > 255:
                    raise ValueError("board cell values must fit in one byte")

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def cols(self) -> list[int]:
        cols = [0] * self.width
        for y, row in enumerate(self.rows):
            bit = 1 << y
            for x, cell in enumerate(row):
                if cell:
                    cols[x] |= bit
        return cols

    @staticmethod
    def empty(width: int = 10, height: int = 40) -> Board:
        return Board(rows=[bytearray(width) for _ in range(height)])

    @staticmethod
    def from_sbp(
        rows: Sequence[Sequence[Any]],
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> Board:
        """Parse SBP board rows, where row 0 is the bottom."""
        parsed_height = 40 if height is None else height
        parsed_width = (
            max((len(row) for row in rows), default=10) if width is None else width
        )
        parsed_rows = [bytearray(parsed_width) for _ in range(parsed_height)]
        for y, row in enumerate(rows):
            if y >= parsed_height:
                break
            for x, cell in enumerate(row):
                if x < parsed_width and cell is not None:
                    parsed_rows[y][x] = cell_value(cell)
        return Board(rows=parsed_rows)

    def occupied(self, x: int, y: int) -> bool:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.rows[y][x] != EMPTY_CELL

    def cell(self, x: int, y: int) -> int:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError(f"cell out of bounds: ({x}, {y})")
        return self.rows[y][x]

    def set_cell(self, x: int, y: int, value: int) -> None:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError(f"cell out of bounds: ({x}, {y})")
        if value < 0 or value > 255:
            raise ValueError("board cell value must fit in one byte")
        self.rows[y][x] = value

    def place(self, piece: Piece, rotation: Rotation, cx: int, cy: int) -> None:
        value = PIECE_TO_CELL[piece]
        for x, y in piece_cells(piece, rotation, cx, cy):
            assert 0 <= x < self.width and 0 <= y < self.height
            self.rows[y][x] = value

    def line_clears(self) -> int:
        """Bitmask of completely filled rows."""
        mask = 0
        for y, row in enumerate(self.rows):
            if all(row):
                mask |= 1 << y
        return mask

    def remove_lines(self, lines: int) -> None:
        """Clear rows indicated by bitmask, shifting rows above down."""
        kept = [row for y, row in enumerate(self.rows) if not (lines & (1 << y))]
        self.rows = kept + [
            bytearray(self.width) for _ in range(self.height - len(kept))
        ]

    def distance_to_ground(self, x: int, y: int) -> int:
        """How many rows cell (x, y) can fall before hitting something."""
        assert 0 <= x < self.width and 0 <= y < self.height
        for yy in range(y - 1, -1, -1):
            if self.rows[yy][x]:
                return y - yy - 1
        return y

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
        return all(not any(row) for row in self.rows)

    def stack_height(self) -> int:
        for y in range(self.height - 1, -1, -1):
            if any(self.rows[y]):
                return y + 1
        return 0

    def occupied_count(self) -> int:
        return sum(1 for row in self.rows for cell in row if cell)

    def apply_garbage(self, rows: Sequence[bytearray | Sequence[int]]) -> bool:
        """Apply arbitrary garbage rows, pushing existing rows upward."""
        insert_rows = [_coerce_row(row) for row in rows]
        if not insert_rows:
            return False
        for y, row in enumerate(insert_rows):
            if len(row) != self.width:
                raise ValueError(f"inserted row {y} must contain {self.width} cells")
        lines = len(insert_rows)
        topped_out = any(any(row) for row in self.rows[max(0, self.height - lines) :])
        shifted = insert_rows[: self.height]
        shifted.extend(self.rows[: max(0, self.height - lines)])
        self.rows = shifted[: self.height]
        return topped_out

    def copy(self) -> Board:
        return Board(rows=[bytearray(row) for row in self.rows])


def cell_value(value: Any) -> int:
    if isinstance(value, str):
        return LABEL_TO_CELL.get(value, GENERIC_FILLED_CELL)
    return GENERIC_FILLED_CELL


def cell_label(value: int) -> str | None:
    if value == EMPTY_CELL:
        return None
    return CELL_TO_LABEL.get(value, "G")


def cell_piece(value: int) -> Piece | None:
    label = cell_label(value)
    if label is None or label == "G":
        return None
    try:
        return Piece(label)
    except ValueError:
        return None


def _coerce_row(row: bytearray | Sequence[int]) -> bytearray:
    if isinstance(row, bytearray):
        return bytearray(row)
    return bytearray(row)
