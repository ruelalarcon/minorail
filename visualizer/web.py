from __future__ import annotations

import html
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from core.board import piece_cells
from core.piece import Piece
from core.rotation import Rotation
from game.rules import Rules
from game.state import GameState
from movegen.pathfinder import MoveStep, apply_step, obstructed
from service.snapshot import SuggestionResult

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
class _RenderCell:
    kind: str
    piece: Optional[Piece] = None


@dataclass(frozen=True)
class _RenderFrame:
    cells: list[list[_RenderCell]]
    active_piece: Optional[Piece]
    active_x: Optional[int]
    active_y: Optional[int]
    active_rotation: Optional[Rotation]
    hold: Optional[Piece]
    queue: list[Piece]
    combo: int
    back_to_back: int
    status: str


class WebVisualizer:
    def __init__(
        self,
        settings: dict[str, Any],
        *,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
    ) -> None:
        self._settings = settings
        cfg = self._settings["visualizer"]
        self._move_delay = cfg["move_delay_ms"] / 1000
        self._lock_delay = cfg["lock_delay_ms"] / 1000
        self._first_move_delay = cfg["first_move_delay_ms"] / 1000
        self._first_spawn = True
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._frame: Optional[_RenderFrame] = None
        self._client_connected = threading.Event()
        self._server_started = False

    @property
    def url(self) -> str:
        if self._port is None:
            return f"http://{self._host}:auto"
        return f"http://{self._host}:{self._port}"

    def on_game_started(self, state: GameState) -> None:
        self._first_spawn = True
        self._ensure_server_started()
        self._render(state, status="Waiting for browser")
        self._wait_for_client()
        self._render(state, status="Game started")

    def on_spawn(self, state: GameState, piece: Piece) -> None:
        self._render(
            state,
            state.active.piece,
            (state.active.x, state.active.y, state.active.rotation),
            status=f"Spawn: {piece.value}",
        )
        if self._first_spawn:
            time.sleep(self._first_move_delay)
            self._first_spawn = False

    def animate_suggestion(
        self,
        state: GameState,
        moving_piece: Piece,
        result: SuggestionResult,
        hold_used: bool,
        rules: Rules,
    ) -> None:
        if hold_used:
            self._render(
                state,
                moving_piece,
                (state.active.x, state.active.y, Rotation.North),
                status="Hold",
            )
            time.sleep(self._lock_delay)

        path = result.path
        if path is not None:
            ax, ay, arot = state.active.x, state.active.y, Rotation.North
            if obstructed(state.board, moving_piece, arot, ax, ay):
                ay = 20
            for step in path[:-1]:
                ax, ay, arot = apply_step(
                    step,
                    moving_piece,
                    arot,
                    ax,
                    ay,
                    state.board,
                    rules.kickset,
                )
                self._render(
                    state,
                    moving_piece,
                    (ax, ay, arot),
                    status=f"Move: {step.value}",
                )
                time.sleep(self._move_delay)
            ax, ay, arot = apply_step(
                MoveStep.HardDrop,
                moving_piece,
                arot,
                ax,
                ay,
                state.board,
                rules.kickset,
            )
            self._render(
                state,
                moving_piece,
                (ax, ay, arot),
                status=f"Move: {MoveStep.HardDrop.value}",
            )
        else:
            self.warning(result.reason or "no path found")
            placement = result.placement
            if placement is not None:
                loc = placement.location
                self._render(
                    state,
                    moving_piece,
                    (loc.x, loc.y, loc.rotation),
                    status=result.reason or "No path",
                )

        time.sleep(self._lock_delay)

    def on_piece_locked(self, state: GameState) -> None:
        self._render(state, status="Locked")
        time.sleep(self._lock_delay * 0.5)

    def on_top_out(self, state: GameState) -> None:
        self._render(state, status="Top out")

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)
        self._set_status(f"Warning: {message}")

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
        self._set_status(f"Error: {message}")

    def _render(
        self,
        state: GameState,
        active_piece: Optional[Piece] = None,
        active_loc: Optional[tuple[int, int, Rotation]] = None,
        *,
        status: str = "",
    ) -> None:
        if active_piece is None or active_loc is None:
            active_piece = state.active.piece
            active_loc = (state.active.x, state.active.y, state.active.rotation)

        cfg = self._settings["visualizer"]
        frame = _make_frame(
            state,
            active_piece,
            active_loc,
            cfg["visible_rows"],
            cfg["queue_size"],
            status,
        )
        with self._lock:
            self._frame = frame

    def _set_status(self, status: str) -> None:
        with self._lock:
            if self._frame is None:
                return
            self._frame = _RenderFrame(
                cells=self._frame.cells,
                active_piece=self._frame.active_piece,
                active_x=self._frame.active_x,
                active_y=self._frame.active_y,
                active_rotation=self._frame.active_rotation,
                hold=self._frame.hold,
                queue=self._frame.queue,
                combo=self._frame.combo,
                back_to_back=self._frame.back_to_back,
                status=status,
            )

    def _ensure_server_started(self) -> None:
        if self._server_started:
            return

        try:
            from nicegui import app, ui
        except ImportError as e:
            raise RuntimeError(
                "The web visualizer dependency is not installed. "
                "Install it with `pip install nicegui`."
            ) from e

        visualizer = self
        if self._port is None:
            self._port = _find_open_port(self._host)

        app.on_connect(lambda: self._client_connected.set())

        @ui.page("/")
        def index() -> None:
            ui.add_head_html(_FONT_LINKS)
            ui.add_css(_CSS)
            ui.query("body").classes("minorail-body")
            with ui.column().classes("minorail-shell"):
                with ui.row().classes("minorail-topbar"):
                    ui.label("minorail").classes("minorail-title")
                    ui.label("web visualizer").classes("minorail-subtitle")
                with ui.row().classes("minorail-main"):
                    board = ui.html(_empty_html()).classes("minorail-board-wrap")
                    side = ui.html("").classes("minorail-side")

            def refresh() -> None:
                frame = visualizer._current_frame()
                if frame is None:
                    return
                board.set_content(_board_html(frame))
                side.set_content(_side_html(frame))

            ui.timer(1 / 30, refresh, active=True)

        thread = threading.Thread(
            target=lambda: ui.run(
                host=self._host,
                port=self._port,
                title="minorail",
                reload=False,
                show=True,
                show_welcome_message=False,
            ),
            name="minorail-web",
            daemon=True,
        )
        thread.start()
        self._server_started = True
        print(f"[info] web visualizer: {self.url}", file=sys.stderr)

    def _current_frame(self) -> Optional[_RenderFrame]:
        with self._lock:
            return self._frame

    def _wait_for_client(self) -> None:
        print("[info] waiting for web visualizer client", file=sys.stderr)
        if self._client_connected.wait(timeout=15):
            return
        raise RuntimeError(f"web visualizer did not open within 15s: {self.url}")


def _make_frame(
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    visible_rows: int,
    queue_size: int,
    status: str,
) -> _RenderFrame:
    cells = [[_RenderCell("empty") for _ in range(10)] for _ in range(visible_rows)]

    for x in range(10):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                cells[y][x] = _RenderCell("filled")

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
                cells[gy][gx] = _RenderCell("ghost", active_piece)
        for ax, ay in piece_cells(active_piece, active_rotation, active_x, active_y):
            if 0 <= ax < 10 and 0 <= ay < visible_rows:
                cells[ay][ax] = _RenderCell("active", active_piece)

    return _RenderFrame(
        cells=cells,
        active_piece=active_piece,
        active_x=active_x,
        active_y=active_y,
        active_rotation=active_rotation,
        hold=state.hold,
        queue=list(state.queue[:queue_size]),
        combo=state.combo,
        back_to_back=state.back_to_back,
        status=status,
    )


def _empty_html() -> str:
    return '<div class="minorail-board"></div>'


def _board_html(frame: _RenderFrame) -> str:
    out = ['<div class="minorail-board">']
    for row in reversed(frame.cells):
        for cell in row:
            classes = f"minorail-cell minorail-cell-{cell.kind}"
            style = ""
            if cell.piece is not None:
                style = f' style="--piece-color: {PIECE_COLORS[cell.piece]}"'
            out.append(f'<div class="{classes}"{style}></div>')
    out.append("</div>")
    return "".join(out)


def _side_html(frame: _RenderFrame) -> str:
    active = _piece_preview(frame.active_piece)
    hold = _piece_preview(frame.hold)
    queue = "".join(_piece_preview(piece) for piece in frame.queue)
    rotation = frame.active_rotation.name if frame.active_rotation is not None else ""
    status = html.escape(frame.status)
    return f"""
    <section class="minorail-panel">
      <div class="minorail-section-title">Active Piece</div>
      <div class="minorail-active">{active}</div>
      <dl class="minorail-stats">
        <div><dt>X</dt><dd>{_value(frame.active_x)}</dd></div>
        <div><dt>Y</dt><dd>{_value(frame.active_y)}</dd></div>
        <div><dt>Orientation</dt><dd>{html.escape(rotation)}</dd></div>
      </dl>
    </section>
    <section class="minorail-panel">
      <div class="minorail-section-title">hold</div>
      <div class="minorail-piece-row">{hold}</div>
    </section>
    <section class="minorail-panel">
      <div class="minorail-section-title">queue</div>
      <div class="minorail-piece-row">{queue}</div>
    </section>
    <section class="minorail-panel">
      <dl class="minorail-stats minorail-large-stats">
        <div><dt>Combo</dt><dd>{frame.combo}</dd></div>
        <div><dt>Back-to-Back</dt><dd>{frame.back_to_back}</dd></div>
      </dl>
    </section>
    <section class="minorail-panel minorail-status">
      <div class="minorail-section-title">status</div>
      {status}
    </section>
    """


def _piece_preview(piece: Optional[Piece]) -> str:
    if piece is None:
        return _empty_piece_preview()

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


def _empty_piece_preview() -> str:
    return '<span class="minorail-piece-preview minorail-piece-empty"></span>'


def _value(value: Optional[int]) -> str:
    return "" if value is None else str(value)


def _find_open_port(host: str) -> int:
    bind_host = "127.0.0.1" if host == "0.0.0.0" else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((bind_host, 0))
        return int(sock.getsockname()[1])


_FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lilex:ital,wght@0,100..700;1,100..700&display=swap" rel="stylesheet">
"""


_CSS = """
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
.minorail-shell {
  width: min(1080px, calc(100vw - 32px));
  margin: 16px auto;
  gap: 12px;
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
.minorail-main {
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
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
