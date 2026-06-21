from __future__ import annotations

import html
import socket
from dataclasses import dataclass
from typing import Optional

from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells

PIECE_COLORS = {
    Piece.I: "#38bdf8",
    Piece.O: "#facc15",
    Piece.T: "#d946ef",
    Piece.L: "#fb923c",
    Piece.J: "#60a5fa",
    Piece.S: "#4ade80",
    Piece.Z: "#f87171",
}


@dataclass(frozen=True)
class RenderCell:
    kind: str
    piece: Optional[Piece] = None


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


def make_board_frame(
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    visible_rows: int,
    queue_size: int,
    *,
    editable: bool = False,
) -> BoardFrame:
    cells = [[RenderCell("empty") for _ in range(10)] for _ in range(visible_rows)]

    for x in range(10):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                cells[y][x] = RenderCell("filled")

    active_x: Optional[int] = None
    active_y: Optional[int] = None
    active_rotation: Optional[Rotation] = None
    if active_piece is not None and active_loc is not None:
        active_x, active_y, active_rotation = active_loc
        drop = state.board.drop_distance(
            active_piece,
            active_rotation,
            active_x,
            active_y,
        )
        for gx, gy in piece_cells(
            active_piece,
            active_rotation,
            active_x,
            active_y - drop,
        ):
            if (
                0 <= gx < 10
                and 0 <= gy < visible_rows
                and cells[gy][gx].kind == "empty"
            ):
                cells[gy][gx] = RenderCell("ghost", active_piece)
        for ax, ay in piece_cells(active_piece, active_rotation, active_x, active_y):
            if 0 <= ax < 10 and 0 <= ay < visible_rows:
                cells[ay][ax] = RenderCell("active", active_piece)

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


def empty_board_html() -> str:
    return '<div class="minorail-board minorail-board-disabled"></div>'


def board_html(frame: BoardFrame) -> str:
    board_class = (
        "minorail-board-editable" if frame.editable else "minorail-board-disabled"
    )
    out = [f'<div class="minorail-board {board_class}">']
    for y in reversed(range(len(frame.cells))):
        for x, cell in enumerate(frame.cells[y]):
            classes = f"minorail-cell minorail-cell-{cell.kind}"
            style = ""
            if cell.piece is not None:
                style = f' style="--piece-color: {PIECE_COLORS[cell.piece]}"'
            out.append(
                f'<div class="{classes}" data-x="{x}" data-y="{y}"{style}></div>'
            )
    out.append("</div>")
    return "".join(out)


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
    color = PIECE_COLORS[piece]
    out = [
        '<span class="minorail-piece-preview" '
        f'aria-label="{html.escape(piece.value)}" '
        f'style="--piece-color: {color}">',
        '<span class="minorail-piece-shape" '
        f'style="--piece-width: {width}; --piece-height: {height}">',
    ]
    for y in reversed(range(height)):
        for x in range(width):
            cell_class = "minorail-preview-cell"
            if (x, y) in occupied:
                cell_class += " minorail-preview-cell-filled"
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
.minorail-body {
  min-height: 100vh;
  background:
    linear-gradient(90deg, rgba(148, 163, 184, 0.04) 1px, transparent 1px),
    linear-gradient(rgba(148, 163, 184, 0.04) 1px, transparent 1px),
    #101216;
  background-size: 28px 28px;
  color: #e7ecf3;
  font-family: Lilex, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-variant-ligatures: contextual;
}
.nicegui-error-popup {
  background: #14171d !important;
  border: 1px solid #47515f !important;
  border-radius: 6px !important;
  color: #e7ecf3 !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.34) !important;
}
.nicegui-error-popup span {
  color: #e7ecf3 !important;
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
  letter-spacing: 0;
  color: #f8fafc;
}
.minorail-title::before {
  content: "./";
  color: #6f7783;
}
.minorail-subtitle {
  color: #8792a2;
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
  width: 36px;
  min-width: 36px;
  height: 36px;
  min-height: 36px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  font-family: inherit;
  text-transform: none;
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
}
.minorail-controls .minorail-icon-button .q-icon {
  font-size: 20px;
}
.minorail-controls .minorail-pause-button {
  background: #93c5fd !important;
  background-color: #93c5fd !important;
  border-color: #bfdbfe !important;
  color: #102a56 !important;
}
.minorail-controls .minorail-pause-button:hover {
  background: #bfdbfe !important;
  background-color: #bfdbfe !important;
}
.minorail-controls .minorail-unpause-button {
  background: #86efac !important;
  background-color: #86efac !important;
  border-color: #bbf7d0 !important;
  color: #12351f !important;
}
.minorail-controls .minorail-unpause-button:hover {
  background: #bbf7d0 !important;
  background-color: #bbf7d0 !important;
}
.minorail-controls .minorail-clear-button {
  background: #fca5a5 !important;
  background-color: #fca5a5 !important;
  border-color: #fecaca !important;
  color: #4a1111 !important;
}
.minorail-controls .minorail-clear-button:hover {
  background: #fecaca !important;
  background-color: #fecaca !important;
}
.minorail-controls .q-btn--disabled {
  background: #2b313b !important;
  background-color: #2b313b !important;
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
  background: #14171d;
  border: 1px solid #343b47;
  border-radius: 6px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
}
.minorail-board {
  display: grid;
  grid-template-columns: repeat(10, minmax(18px, 32px));
  grid-auto-rows: minmax(18px, 32px);
  gap: 1px;
  background: #1a2029;
  border: 1px solid #48515f;
  border-radius: 4px;
  padding: 5px;
  overflow: hidden;
}
.minorail-cell {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  background: #0e1218;
  border: 1px solid rgba(122, 134, 153, 0.07);
  user-select: none;
}
.minorail-board-disabled {
  cursor: not-allowed;
}
.minorail-board-disabled .minorail-cell {
  cursor: not-allowed;
}
.minorail-board-editable {
  cursor: cell;
}
.minorail-board-editable .minorail-cell {
  cursor: cell;
}
.minorail-cell-filled {
  background: #7f8896;
  border-color: rgba(235, 240, 247, 0.42);
}
.minorail-cell-active {
  background: var(--piece-color);
  border-color: rgba(255, 255, 255, 0.58);
}
.minorail-cell-filled::before,
.minorail-cell-filled::after,
.minorail-cell-active::before,
.minorail-cell-active::after {
  content: "";
  position: absolute;
  width: 0;
  height: 0;
}
.minorail-cell-filled::before,
.minorail-cell-active::before {
  top: 0;
  left: 0;
  border-top: 9px solid rgba(255, 255, 255, 0.22);
  border-right: 9px solid transparent;
}
.minorail-cell-active::before {
  border-top-color: color-mix(in srgb, var(--piece-color), white 34%);
}
.minorail-cell-filled::after,
.minorail-cell-active::after {
  right: 0;
  bottom: 0;
  border-bottom: 6px solid rgba(0, 0, 0, 0.2);
  border-left: 6px solid transparent;
}
.minorail-cell-active::after {
  border-bottom-color: color-mix(in srgb, var(--piece-color), black 28%);
}
.minorail-cell-ghost {
  background: color-mix(in srgb, var(--piece-color), transparent 90%);
  border: 1px dashed color-mix(in srgb, var(--piece-color), white 4%);
}
.minorail-side {
  width: min(350px, calc(100vw - 32px));
}
.minorail-panel {
  background: #14171d;
  border: 1px solid #343b47;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}
.minorail-section-title {
  color: #8d99a8;
  font-size: 12px;
  line-height: 16px;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0;
  margin-bottom: 9px;
}
.minorail-section-title::before {
  content: "$ ";
  color: #6f7783;
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
  width: 54px;
  height: 43px;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: #0d1015;
  border: 1px solid #303844;
}
.minorail-piece-empty {
  background: #0d1015;
  border: 1px solid #303844;
}
.minorail-piece-shape {
  display: grid;
  grid-template-columns: repeat(var(--piece-width), 9px);
  grid-template-rows: repeat(var(--piece-height), 9px);
  gap: 2px;
}
.minorail-preview-cell {
  width: 9px;
  height: 9px;
  background: transparent;
  border-radius: 2px;
}
.minorail-preview-cell-filled {
  background: var(--piece-color);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.28),
    inset 0 -2px 0 rgba(0, 0, 0, 0.18);
}
.minorail-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}
.minorail-large-stats {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.minorail-single-stat {
  grid-template-columns: minmax(0, 1fr);
}
.minorail-stats div {
  min-width: 0;
  background: #0d1015;
  border: 1px solid #252c36;
  border-radius: 4px;
  padding: 8px;
}
.minorail-stats dt {
  color: #8792a2;
  font-size: 11px;
  line-height: 16px;
  margin-bottom: 2px;
}
.minorail-stats dd {
  color: #eef2f7;
  font-size: 17px;
  line-height: 22px;
  font-weight: 650;
  margin: 0;
  overflow-wrap: anywhere;
}
.minorail-status {
  color: #d4dbe5;
  min-height: 58px;
  line-height: 20px;
}
@media (max-width: 720px) {
  .minorail-shell {
    width: min(100vw - 20px, 440px);
    margin: 10px auto;
  }
  .minorail-solo-shell {
    width: min(100vw - 20px, 440px);
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
    width: 100%;
    padding: 8px;
  }
  .minorail-board {
    grid-template-columns: repeat(10, minmax(0, 1fr));
    grid-auto-rows: auto;
  }
  .minorail-side {
    width: 100%;
  }
}
"""
