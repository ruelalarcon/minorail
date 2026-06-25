from __future__ import annotations

import html
import socket
from dataclasses import dataclass, field
from typing import Optional

from tetris.game.state import GameState
from tetris.model.board import cell_piece
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells


class CellKind:
    EMPTY = "empty"
    FILLED = "filled"
    ACTIVE = "active"
    GHOST = "ghost"
    GARBAGE = "garbage"


OCCUPIED_KINDS = frozenset({CellKind.FILLED, CellKind.ACTIVE, CellKind.GARBAGE})

BORDER_SIDES = ("top", "right", "bottom", "left")

DEFAULT_PIECE_COLOR = "#7f8896"
DEFAULT_PIECE_HIGHLIGHT = "#c7d0dd"

PIECE_COLORS = {
    Piece.I: "#42afe1",
    Piece.O: "#f6d03c",
    Piece.T: "#b94bc6",
    Piece.L: "#f38927",
    Piece.J: "#1165b5",
    Piece.S: "#51b84d",
    Piece.Z: "#eb4f65",
}

PIECE_HIGHLIGHT_COLORS = {
    Piece.I: "#6ceaff",
    Piece.O: "#ffff7f",
    Piece.T: "#d958e9",
    Piece.L: "#ffba59",
    Piece.J: "#339bff",
    Piece.S: "#84f880",
    Piece.Z: "#ff7f79",
}

GARBAGE_COLOR = "#868686"
GARBAGE_HIGHLIGHT_COLOR = "#dddddd"
GHOST_BORDER_LIGHTEN = "18%"


@dataclass(frozen=True)
class RenderCell:
    kind: str
    piece: Optional[Piece] = None
    exposed_top: bool = False
    ghost_borders: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class BoardFrame:
    cells: list[list[RenderCell]]
    active_piece: Optional[Piece]
    active_x: Optional[int]
    active_y: Optional[int]
    active_rotation: Optional[Rotation]
    hold: Optional[Piece]
    queue: list[Piece]
    combo: int
    back_to_back: int
    editable: bool = False

    @property
    def width(self) -> int:
        return len(self.cells[0]) if self.cells else 0

    @property
    def height(self) -> int:
        return len(self.cells)


def piece_palette(piece: Piece) -> tuple[str, str]:
    return (
        PIECE_COLORS.get(piece, DEFAULT_PIECE_COLOR),
        PIECE_HIGHLIGHT_COLORS.get(piece, DEFAULT_PIECE_HIGHLIGHT),
    )


def cell_palette(cell: RenderCell) -> tuple[str, str]:
    if cell.kind == CellKind.GARBAGE:
        return GARBAGE_COLOR, GARBAGE_HIGHLIGHT_COLOR
    if cell.piece is not None:
        return piece_palette(cell.piece)
    return DEFAULT_PIECE_COLOR, DEFAULT_PIECE_HIGHLIGHT


def make_board_frame(
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    visible_rows: int,
    queue_size: int,
    *,
    editable: bool = False,
) -> BoardFrame:
    width = state.board.width
    visible_rows = min(visible_rows, state.board.height)
    cells: list[list[RenderCell]] = [
        [RenderCell(CellKind.EMPTY) for _ in range(width)] for _ in range(visible_rows)
    ]

    _populate_static_cells(cells, state, width, visible_rows)
    active_x, active_y, active_rotation = _populate_active_piece(
        cells, state, active_piece, active_loc, width, visible_rows
    )
    _mark_exposed_tops(cells, width, visible_rows)
    _mark_ghost_borders(cells, width, visible_rows)

    return BoardFrame(
        cells=cells,
        active_piece=active_piece,
        active_x=active_x,
        active_y=active_y,
        active_rotation=active_rotation,
        hold=state.hold,
        queue=list(state.queue[:queue_size]),
        combo=state.combo,
        back_to_back=state.back_to_back,
        editable=editable,
    )


def _populate_static_cells(
    cells: list[list[RenderCell]],
    state: GameState,
    width: int,
    visible_rows: int,
) -> None:
    for x in range(width):
        for y in range(visible_rows):
            if not state.board.occupied(x, y):
                continue
            piece = cell_piece(state.board.cell(x, y))
            kind = CellKind.GARBAGE if piece is None else CellKind.FILLED
            cells[y][x] = RenderCell(kind, piece)


def _populate_active_piece(
    cells: list[list[RenderCell]],
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    width: int,
    visible_rows: int,
) -> tuple[Optional[int], Optional[int], Optional[Rotation]]:
    if active_piece is None or active_loc is None:
        return None, None, None
    active_x, active_y, active_rotation = active_loc
    drop = state.board.drop_distance(active_piece, active_rotation, active_x, active_y)
    for gx, gy in piece_cells(active_piece, active_rotation, active_x, active_y - drop):
        if (
            0 <= gx < width
            and 0 <= gy < visible_rows
            and cells[gy][gx].kind == CellKind.EMPTY
        ):
            cells[gy][gx] = RenderCell(CellKind.GHOST, active_piece)
    for ax, ay in piece_cells(active_piece, active_rotation, active_x, active_y):
        if 0 <= ax < width and 0 <= ay < visible_rows:
            cells[ay][ax] = RenderCell(CellKind.ACTIVE, active_piece)
    return active_x, active_y, active_rotation


def _mark_exposed_tops(
    cells: list[list[RenderCell]], width: int, visible_rows: int
) -> None:
    for x in range(width):
        for y in range(visible_rows):
            cell = cells[y][x]
            if cell.kind not in OCCUPIED_KINDS:
                continue
            if y + 1 >= visible_rows or cells[y + 1][x].kind in (
                CellKind.EMPTY,
                CellKind.GHOST,
            ):
                cells[y][x] = RenderCell(
                    cell.kind, cell.piece, True, cell.ghost_borders
                )


def _mark_ghost_borders(
    cells: list[list[RenderCell]], width: int, visible_rows: int
) -> None:
    for x in range(width):
        for y in range(visible_rows):
            cell = cells[y][x]
            if cell.kind != CellKind.GHOST:
                continue
            borders: set[str] = set()
            if y - 1 < 0 or cells[y - 1][x].kind != CellKind.GHOST:
                borders.add("bottom")
            if y + 1 >= visible_rows or cells[y + 1][x].kind != CellKind.GHOST:
                borders.add("top")
            if x + 1 >= width or cells[y][x + 1].kind != CellKind.GHOST:
                borders.add("right")
            if x - 1 < 0 or cells[y][x - 1].kind != CellKind.GHOST:
                borders.add("left")
            cells[y][x] = RenderCell(
                cell.kind, cell.piece, cell.exposed_top, frozenset(borders)
            )


def empty_board_html() -> str:
    return '<div class="minorail-board minorail-board-disabled"></div>'


def board_html(frame: BoardFrame) -> str:
    board_class = (
        "minorail-board-editable" if frame.editable else "minorail-board-disabled"
    )
    out = [
        f'<div class="minorail-board {board_class}" '
        f'style="--board-width: {frame.width}">'
    ]
    for y in reversed(range(frame.height)):
        for x, cell in enumerate(frame.cells[y]):
            out.append(_cell_html(x, y, cell))
    out.append("</div>")
    return "".join(out)


def _cell_html(x: int, y: int, cell: RenderCell) -> str:
    return (
        f'<div class="{_cell_classes(x, y, cell)}"'
        f' data-x="{x}" data-y="{y}"{_cell_style(cell)}></div>'
    )


def _cell_classes(x: int, y: int, cell: RenderCell) -> str:
    classes = f"minorail-cell minorail-cell-{cell.kind}"
    if (x + y) % 2 == 1:
        classes += " minorail-cell-odd"
    if cell.exposed_top:
        classes += " minorail-cell-exposed-top"
    return classes


def _cell_style(cell: RenderCell) -> str:
    color, highlight = cell_palette(cell)
    parts: list[str] = [
        f"--piece-color: {color}",
        f"--piece-highlight: {highlight}",
    ]
    if cell.ghost_borders and cell.piece is not None:
        base_color, _ = piece_palette(cell.piece)
        border_color = f"color-mix(in srgb, {base_color}, white {GHOST_BORDER_LIGHTEN})"
        for side in BORDER_SIDES:
            if side in cell.ghost_borders:
                parts.append(f"border-{side}: 1px solid {border_color}")
    return f' style="{"; ".join(parts)}"'


def piece_preview(piece: Optional[Piece]) -> str:
    if piece is None:
        return empty_piece_preview()

    cells = piece_cells(piece, Rotation.North, 0, 0)
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    normalized = [(x - min_x, y - min_y) for x, y in cells]
    width = max(x for x, _ in normalized) + 1
    height = max(y for _, y in normalized) + 1
    occupied = set(normalized)
    color, highlight = piece_palette(piece)
    out = [
        '<span class="minorail-piece-preview" '
        f'aria-label="{html.escape(piece.value)}" '
        f'style="--piece-color: {color}; --piece-highlight: {highlight}">',
        '<span class="minorail-piece-shape" '
        f'style="--piece-width: {width}; --piece-height: {height}">',
    ]
    for y in reversed(range(height)):
        for x in range(width):
            cell_class = "minorail-preview-cell"
            if (x, y) in occupied:
                cell_class += " minorail-preview-cell-filled"
                if y + 1 >= height or (x, y + 1) not in occupied:
                    cell_class += " minorail-preview-cell-exposed-top"
            out.append(f'<span class="{cell_class}"></span>')
    out.append("</span></span>")
    return "".join(out)


def empty_piece_preview() -> str:
    return '<span class="minorail-piece-preview minorail-piece-empty"></span>'


def value(value: Optional[int]) -> str:
    return "" if value is None else str(value)


def find_open_port(host: str) -> int:
    bind_host = "127.0.0.1" if host == "0.0.0.0" else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((bind_host, 0))
        return int(sock.getsockname()[1])


FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lilex:ital,wght@0,100..700;1,100..700&display=swap" rel="stylesheet">
"""


BOARD_SCRIPT = """
<script>
(() => {
  let paintMode = null;
  let lastCell = "";
  let requestChain = Promise.resolve();

  const postJson = (url, payload) => {
    requestChain = requestChain.then(() => fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    })).catch(() => {});
  };

  const paint = cell => {
    if (!cell || paintMode === null) return;
    const key = `${cell.dataset.x}:${cell.dataset.y}:${paintMode}`;
    if (key === lastCell) return;
    lastCell = key;
    postJson("/minorail/api/cell", {
      x: Number(cell.dataset.x),
      y: Number(cell.dataset.y),
      filled: paintMode,
    });
  };

  document.addEventListener("contextmenu", event => {
    if (event.target.closest(".minorail-cell")) event.preventDefault();
  });

  document.addEventListener("mousedown", event => {
    const cell = event.target.closest(".minorail-cell");
    if (!cell) return;
    if (event.button !== 0 && event.button !== 2) return;
    event.preventDefault();
    paintMode = event.button === 0;
    lastCell = "";
    paint(cell);
  });

  document.addEventListener("mouseover", event => {
    if (paintMode === null) return;
    paint(event.target.closest(".minorail-cell"));
  });

  document.addEventListener("mouseup", () => {
    paintMode = null;
    lastCell = "";
  });

  window.addEventListener("blur", () => {
    paintMode = null;
    lastCell = "";
  });
})();
</script>
"""


CSS = """
:root {
  --minorail-bg: #101216;
  --minorail-panel-bg: #14171d;
  --minorail-cell-bg: #14171d;
  --minorail-cell-bg-odd: #161922;
  --minorail-field-bg: #0d1015;
  --minorail-border: #343b47;
  --minorail-field-border: #252c36;
  --minorail-text: #e7ecf3;
  --minorail-text-dim: #8792a2;
  --minorail-text-faint: #8d99a8;
  --minorail-accent: #6f7783;
  --minorail-highlight: 14%;
  --minorail-board-cell-min: 18px;
  --minorail-board-cell-max: 32px;
}
.minorail-body {
  min-height: 100vh;
  background:
    linear-gradient(90deg, rgb(148 163 184 / 0.04) 1px, transparent 1px),
    linear-gradient(rgb(148 163 184 / 0.04) 1px, transparent 1px),
    var(--minorail-bg);
  background-size: 28px 28px;
  color: var(--minorail-text);
  font-family: Lilex, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-variant-ligatures: contextual;
}
.nicegui-error-popup {
  background: var(--minorail-panel-bg) !important;
  border: 1px solid #47515f !important;
  border-radius: 6px !important;
  color: var(--minorail-text) !important;
  box-shadow: 0 20px 60px rgb(0 0 0 / 0.34) !important;
}
.minorail-shell {
  width: min(1080px, calc(100vw - 32px));
  margin: 16px auto;
  gap: 12px;
}
.minorail-solo-shell {
  width: fit-content;
  max-width: calc(100vw - 32px);
}
.minorail-topbar {
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  border-bottom: 1px solid #2d333d;
  padding-bottom: 10px;
}
.minorail-title {
  font-size: 20px;
  line-height: 26px;
  font-weight: 650;
  color: #f8fafc;
}
.minorail-title::before {
  content: "./";
  color: var(--minorail-accent);
}
.minorail-subtitle {
  color: var(--minorail-text-dim);
  font-size: 13px;
  line-height: 18px;
  font-weight: 500;
}
.minorail-controls {
  align-items: center;
  gap: 8px;
  width: 100%;
}
.minorail-controls .minorail-icon-button {
  inline-size: 36px;
  block-size: 36px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  font-family: inherit;
  text-transform: none;
  box-shadow: 0 10px 22px rgb(0 0 0 / 0.22);
}
.minorail-controls .minorail-icon-button .q-icon {
  font-size: 20px;
}
.minorail-controls .minorail-pause-button {
  background: #93c5fd !important;
  border-color: #bfdbfe !important;
  color: #102a56 !important;
}
.minorail-controls .minorail-pause-button:hover {
  background: #bfdbfe !important;
}
.minorail-controls .minorail-unpause-button {
  background: #86efac !important;
  border-color: #bbf7d0 !important;
  color: #12351f !important;
}
.minorail-controls .minorail-unpause-button:hover {
  background: #bbf7d0 !important;
}
.minorail-controls .minorail-clear-button {
  background: #fca5a5 !important;
  border-color: #fecaca !important;
  color: #4a1111 !important;
}
.minorail-controls .minorail-clear-button:hover {
  background: #fecaca !important;
}
.minorail-controls .q-btn--disabled {
  background: #2b313b !important;
  border-color: #47515f !important;
  color: #9aa5b5 !important;
  opacity: 1 !important;
  box-shadow: none;
}
.minorail-main {
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.minorail-board-column {
  gap: 8px;
}
.minorail-board-wrap {
  padding: 12px;
  background: var(--minorail-panel-bg);
  border: 1px solid var(--minorail-border);
  border-radius: 6px;
  box-shadow: 0 20px 60px rgb(0 0 0 / 0.28);
}
.minorail-board {
  display: grid;
  grid-template-columns:
    repeat(var(--board-width, 10), minmax(var(--minorail-board-cell-min), var(--minorail-board-cell-max)));
  grid-auto-rows: minmax(var(--minorail-board-cell-min), var(--minorail-board-cell-max));
  background: var(--minorail-panel-bg);
  border: 1px solid var(--minorail-border);
  border-radius: 4px;
  overflow: hidden;
}
.minorail-cell {
  position: relative;
  aspect-ratio: 1;
  user-select: none;
}
.minorail-cell-empty {
  background: var(--minorail-cell-bg);
}
.minorail-cell-empty.minorail-cell-odd {
  background: var(--minorail-cell-bg-odd);
}
.minorail-cell-filled,
.minorail-cell-garbage {
  background: var(--piece-color, #7f8896);
}
.minorail-cell-active {
  background: var(--piece-color);
}
.minorail-cell-ghost {
  background: color-mix(in srgb, var(--piece-color), transparent 80%);
}
.minorail-cell-exposed-top::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  block-size: var(--minorail-highlight);
  background: var(--piece-highlight, rgb(255 255 255 / 0.4));
  pointer-events: none;
}
.minorail-board-disabled,
.minorail-board-disabled .minorail-cell {
  cursor: not-allowed;
}
.minorail-board-editable,
.minorail-board-editable .minorail-cell {
  cursor: cell;
}
.minorail-side {
  width: min(350px, calc(100vw - 32px));
}
.minorail-panel {
  background: var(--minorail-panel-bg);
  border: 1px solid var(--minorail-border);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}
.minorail-section-title {
  color: var(--minorail-text-faint);
  font-size: 12px;
  line-height: 16px;
  font-weight: 650;
  text-transform: uppercase;
  margin-bottom: 9px;
}
.minorail-section-title::before {
  content: "$ ";
  color: var(--minorail-accent);
}
.minorail-active {
  margin-bottom: 12px;
}
.minorail-piece-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.minorail-piece-preview {
  display: inline-flex;
  inline-size: 54px;
  block-size: 43px;
  align-items: center;
  justify-content: center;
  background: var(--minorail-field-bg);
  border: 1px solid var(--minorail-field-border);
  border-radius: 4px;
  overflow: hidden;
}
.minorail-piece-shape {
  display: grid;
  grid-template-columns: repeat(var(--piece-width), 10px);
  grid-template-rows: repeat(var(--piece-height), 10px);
}
.minorail-preview-cell {
  position: relative;
  background: transparent;
}
.minorail-preview-cell-filled {
  background: var(--piece-color);
}
.minorail-preview-cell-exposed-top::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  block-size: var(--minorail-highlight);
  background: var(--piece-highlight, rgb(255 255 255 / 0.4));
  pointer-events: none;
}
.minorail-stats,
.minorail-stats-layout {
  display: grid;
  gap: 8px;
  margin: 0;
}
.minorail-stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.minorail-stats-layout {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.minorail-stats-layout .minorail-stat-wide {
  grid-column: 1 / -1;
}
.minorail-stats div,
.minorail-stats-layout div {
  min-width: 0;
  background: var(--minorail-field-bg);
  border: 1px solid var(--minorail-field-border);
  border-radius: 4px;
  padding: 8px;
}
.minorail-stats dt,
.minorail-stats-layout dt {
  color: var(--minorail-text-dim);
  font-size: 11px;
  line-height: 16px;
  margin-bottom: 2px;
}
.minorail-stats dd,
.minorail-stats-layout dd {
  color: #eef2f7;
  font-size: 13px;
  line-height: 18px;
  font-weight: 500;
  margin: 0;
  overflow-wrap: anywhere;
}
@media (max-width: 720px) {
  .minorail-shell,
  .minorail-solo-shell {
    width: min(100vw - 20px, 440px);
  }
  .minorail-shell {
    margin: 10px auto;
  }
  .minorail-topbar {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }
  .minorail-main {
    gap: 12px;
  }
  .minorail-board-wrap {
    inline-size: 100%;
    padding: 8px;
  }
  .minorail-board {
    grid-template-columns: repeat(var(--board-width, 10), minmax(0, 1fr));
    grid-auto-rows: auto;
  }
  .minorail-side {
    inline-size: 100%;
  }
}
"""
