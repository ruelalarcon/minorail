from __future__ import annotations

import html
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from contracts.suggestion_result import SuggestionResult
from settings import VisualizerSettings
from solo.runner.controls import GameControls
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.movegen.pathfinder import MoveStep, apply_step, obstructed
from visualizers.shared.web import (
    BOARD_SCRIPT,
    CSS,
    FONT_LINKS,
    BoardFrame,
    board_html,
    empty_board_html,
    find_open_port,
    make_board_frame,
    piece_preview,
    value,
)
from visualizers.shared.status import VisualizerStatus


@dataclass(frozen=True)
class _RenderFrame:
    board: BoardFrame
    status: str
    paused: bool
    editable: bool
    total_attack: int

    @property
    def active_x(self) -> Optional[int]:
        return self.board.active_x

    @property
    def active_y(self) -> Optional[int]:
        return self.board.active_y

    @property
    def active_rotation(self) -> Optional[Rotation]:
        return self.board.active_rotation


class WebVisualizer:
    default_pathfinding = True

    def __init__(
        self,
        settings: VisualizerSettings,
        *,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
    ) -> None:
        self._settings = settings
        self._move_delay = settings.move_delay_ms / 1000
        self._lock_delay = settings.lock_delay_ms / 1000
        self._first_move_delay = settings.first_move_delay_ms / 1000
        self._first_spawn = True
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._frame: Optional[_RenderFrame] = None
        self._status = VisualizerStatus()
        self._total_attack = 0
        self._client_connected = threading.Event()
        self._server_started = False
        self._pause_requested = False
        self._pause_boundary_active = False
        self._paused = False
        self._editable = False
        self._pause_condition = threading.Condition()
        self._controls: Optional[GameControls] = None

    @property
    def url(self) -> str:
        if self._port is None:
            return f"http://{self._host}:auto"
        return f"http://{self._host}:{self._port}"

    def set_game_controls(self, controls: GameControls) -> None:
        self._controls = controls

    def on_game_started(self, state: GameState) -> None:
        self._total_attack = 0
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

    def on_piece_locked(self, state: GameState, *, total_attack: int) -> None:
        self._total_attack = total_attack
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

        self._status.set(status)
        board = make_board_frame(
            state,
            active_piece,
            active_loc,
            self._settings.visible_rows,
            self._settings.queue_size,
            editable=self._editable,
        )
        frame = _RenderFrame(
            board=board,
            status=self._status.text,
            paused=self._paused,
            editable=self._editable,
            total_attack=self._total_attack,
        )
        with self._lock:
            self._frame = frame

    def _set_status(self, status: str) -> None:
        with self._lock:
            self._status.set(status)
            if self._frame is None:
                return
            self._frame = _RenderFrame(
                board=self._frame.board,
                status=self._status.text,
                paused=self._paused,
                editable=self._editable,
                total_attack=self._frame.total_attack,
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
            self._port = find_open_port(self._host)

        app.on_connect(lambda: self._client_connected.set())

        @ui.page("/")
        def index() -> None:
            ui.add_head_html(FONT_LINKS)
            ui.add_css(CSS)
            ui.add_body_html(BOARD_SCRIPT)
            ui.query("body").classes("minorail-body")
            with ui.column().classes("minorail-shell minorail-solo-shell"):
                with ui.row().classes("minorail-topbar"):
                    ui.label("minorail").classes("minorail-title")
                    ui.label("solo web visualizer").classes("minorail-subtitle")
                with ui.row().classes("minorail-main"):
                    with ui.column().classes("minorail-board-column"):
                        board = ui.html(empty_board_html()).classes(
                            "minorail-board-wrap"
                        )
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
                board.set_content(board_html(frame.board))
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


def _side_html(frame: _RenderFrame) -> str:
    board = frame.board
    active = piece_preview(board.active_piece)
    hold = piece_preview(board.hold)
    queue = "".join(piece_preview(piece) for piece in board.queue)
    rotation = board.active_rotation.name if board.active_rotation is not None else ""
    status = html.escape(frame.status)
    return f"""
    <section class="minorail-panel">
      <div class="minorail-section-title">Active Piece</div>
      <div class="minorail-active">{active}</div>
      <dl class="minorail-stats">
        <div><dt>X</dt><dd>{value(board.active_x)}</dd></div>
        <div><dt>Y</dt><dd>{value(board.active_y)}</dd></div>
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
        <div><dt>Combo</dt><dd>{board.combo}</dd></div>
        <div><dt>Back-to-Back</dt><dd>{board.back_to_back}</dd></div>
      </dl>
    </section>
    <section class="minorail-panel">
      <dl class="minorail-stats minorail-single-stat">
        <div><dt>Total Attack</dt><dd>{frame.total_attack}</dd></div>
      </dl>
    </section>
    <section class="minorail-panel minorail-status">
      <div class="minorail-section-title">status</div>
      {status}
    </section>
    """
