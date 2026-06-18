from __future__ import annotations

import html
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells
from runner.visualizer_protocol import EngineControls
from tetris.model.rules import Rules
from tetris.game.state import GameState
from tetris.movegen.pathfinder import MoveStep, apply_step, obstructed
from suggestion.contracts.suggestion_result import SuggestionResult

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
    paused: bool
    editable: bool


class WebVisualizer:
    default_pathfinding = True

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
        self._pause_requested = False
        self._pause_boundary_active = False
        self._paused = False
        self._editable = False
        self._pause_condition = threading.Condition()
        self._controls: Optional[EngineControls] = None

    @property
    def url(self) -> str:
        if self._port is None:
            return f"http://{self._host}:auto"
        return f"http://{self._host}:{self._port}"

    def set_engine_controls(self, controls: EngineControls) -> None:
        self._controls = controls

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
            placement = result.placement
            if placement is not None:
                loc = placement.location
                self._render(
                    state,
                    moving_piece,
                    (loc.x, loc.y, loc.rotation),
                    status=result.reason or "Placement selected",
                )

        time.sleep(self._lock_delay)

    def on_piece_locked(self, state: GameState) -> None:
        self._render(state, status="Locked")
        time.sleep(self._lock_delay * 0.5)
        self._wait_while_paused(state)

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
            self._paused,
            self._editable,
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
                paused=self._paused,
                editable=self._editable,
            )

    def _toggle_pause(self) -> bool:
        status: Optional[str] = None
        with self._pause_condition:
            if self._paused:
                self._pause_requested = False
                self._paused = False
                self._editable = False
                status = "Resuming"
            elif self._pause_boundary_active:
                self._pause_requested = True
                self._paused = True
                status = "Paused"
            else:
                self._pause_requested = not self._pause_requested
            paused = self._paused
            self._pause_condition.notify_all()

        if status is not None:
            self._set_status(status)
        return paused

    def _edit_cell(self, x: int, y: int, filled: bool) -> dict[str, object]:
        if not self._editable:
            return {"ok": False, "reason": "not editable"}
        if self._controls is None:
            return {"ok": False, "reason": "controls not configured"}
        self._controls.set_cell(x, y, filled)
        self._render(self._controls.get_state(), status="Paused")
        return {"ok": True}

    def _clear(self) -> dict[str, object]:
        if not self._editable:
            return {"ok": False, "reason": "not editable"}
        if self._controls is None:
            return {"ok": False, "reason": "controls not configured"}
        self._controls.clear_board()
        self._render(self._controls.get_state(), status="Paused")
        return {"ok": True}

    def _wait_while_paused(self, state: GameState) -> None:
        with self._pause_condition:
            if not self._pause_requested:
                return
            self._pause_boundary_active = True
            self._paused = True
            self._editable = True
        self._render(state, status="Paused")

        try:
            with self._pause_condition:
                while self._pause_requested:
                    self._pause_condition.wait(timeout=0.1)
        finally:
            with self._pause_condition:
                self._paused = False
                self._editable = False
                self._pause_boundary_active = False
            current = (
                self._controls.get_state() if self._controls is not None else state
            )
            self._render(current, status="Resuming")

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
            ui.add_body_html(_BOARD_SCRIPT)
            ui.query("body").classes("minorail-body")
            with ui.column().classes("minorail-shell"):
                with ui.row().classes("minorail-topbar"):
                    ui.label("minorail").classes("minorail-title")
                    ui.label("web visualizer").classes("minorail-subtitle")
                with ui.row().classes("minorail-main"):
                    with ui.column().classes("minorail-board-column"):
                        board = ui.html(_empty_html()).classes("minorail-board-wrap")
                        with ui.row().classes("minorail-controls"):
                            pause_button = ui.button(
                                icon="pause",
                                on_click=visualizer._toggle_pause,
                                color=None,
                            )
                            pause_button.props("unelevated")
                            pause_button.classes(
                                "minorail-icon-button minorail-pause-button"
                            )
                            pause_button.tooltip("Pause / Unpause")
                            clear_button = ui.button(
                                icon="delete_sweep",
                                on_click=visualizer._clear,
                                color=None,
                            )
                            clear_button.props("unelevated")
                            clear_button.classes(
                                "minorail-icon-button minorail-clear-button"
                            )
                            clear_button.tooltip("Clear Board")
                    side = ui.html("").classes("minorail-side")

            def refresh() -> None:
                frame = visualizer._current_frame()
                if frame is None:
                    return
                board.set_content(_board_html(frame))
                side.set_content(_side_html(frame))
                pause_button.set_icon("play_arrow" if frame.paused else "pause")
                if frame.paused:
                    pause_button.classes(
                        remove="minorail-pause-button",
                        add="minorail-unpause-button",
                    )
                else:
                    pause_button.classes(
                        remove="minorail-unpause-button",
                        add="minorail-pause-button",
                    )
                if frame.editable:
                    clear_button.enable()
                else:
                    clear_button.disable()

            ui.timer(1 / 30, refresh, active=True)

        @app.post("/minorail/api/pause")
        async def toggle_pause() -> dict[str, bool]:
            paused = visualizer._toggle_pause()
            return {"paused": paused}

        @app.post("/minorail/api/cell")
        async def edit_cell(payload: dict[str, Any]) -> dict[str, object]:
            return visualizer._edit_cell(
                int(payload["x"]),
                int(payload["y"]),
                bool(payload["filled"]),
            )

        @app.post("/minorail/api/clear")
        async def clear_board() -> dict[str, object]:
            return visualizer._clear()

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
    paused: bool,
    editable: bool,
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
        paused=paused,
        editable=editable,
    )


def _empty_html() -> str:
    return '<div class="minorail-board minorail-board-disabled"></div>'


def _board_html(frame: _RenderFrame) -> str:
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


_BOARD_SCRIPT = """
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
