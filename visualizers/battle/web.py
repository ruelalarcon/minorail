from __future__ import annotations

import html
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from contracts.suggestion_result import SuggestionResult
from settings import VisualizerSettings
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.movegen.pathfinder import MoveStep, apply_step, obstructed
from visualizers.shared.web import (
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
class _PlayerFrame:
    name: str
    board: BoardFrame
    incoming_garbage: int
    status: str


@dataclass(frozen=True)
class _RenderFrame:
    players: dict[str, _PlayerFrame]


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
        self._status = VisualizerStatus(("A", "B"))
        self._client_connected = threading.Event()
        self._server_started = False
        self._active: dict[str, tuple[Piece, tuple[int, int, Rotation]] | None] = {
            "A": None,
            "B": None,
        }

    @property
    def url(self) -> str:
        if self._port is None:
            return f"http://{self._host}:auto"
        return f"http://{self._host}:{self._port}"

    def on_game_started(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        self._first_spawn = True
        self._active = {name: None for name in states}
        self._ensure_server_started()
        self._status.reset_players("Waiting for browser")
        self._render(states, incoming_garbage)
        self._wait_for_client()
        self._status.reset_players("Battle started")
        self._render(states, incoming_garbage)

    def on_spawn(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        piece: Piece,
    ) -> None:
        state = states[player]
        self._active[player] = (piece, (state.active.x, state.active.y, Rotation.North))
        self._status.set_player(player, f"Spawn: {piece.value}")
        self._render(states, incoming_garbage)
        if self._first_spawn:
            time.sleep(self._first_move_delay)
            self._first_spawn = False

    def animate_suggestion(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        moving_piece: Piece,
        result: SuggestionResult,
        hold_used: bool,
        rules: Rules,
    ) -> None:
        state = states[player]
        if hold_used:
            self._active[player] = (
                moving_piece,
                (state.active.x, state.active.y, Rotation.North),
            )
            self._status.set_player(player, "Hold")
            self._render(states, incoming_garbage)
            time.sleep(self._lock_delay)

        if result.path is not None:
            ax, ay, arot = state.active.x, state.active.y, Rotation.North
            if obstructed(state.board, moving_piece, arot, ax, ay):
                ay = 20
            for step in result.path[:-1]:
                ax, ay, arot = apply_step(
                    step,
                    moving_piece,
                    arot,
                    ax,
                    ay,
                    state.board,
                    rules.kickset,
                )
                self._active[player] = (moving_piece, (ax, ay, arot))
                self._status.set_player(player, f"Move: {step.value}")
                self._render(states, incoming_garbage)
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
            self._active[player] = (moving_piece, (ax, ay, arot))
            self._status.set_player(player, f"Move: {MoveStep.HardDrop.value}")
            self._render(states, incoming_garbage)
        elif result.placement is not None:
            loc = result.placement.location
            self._active[player] = (moving_piece, (loc.x, loc.y, loc.rotation))
            self._status.set_player(player, result.reason or "Placement selected")
            self._render(states, incoming_garbage)

        time.sleep(self._lock_delay)

    def on_piece_locked(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        self._active[player] = None
        self._status.set_player(player, "Locked")
        self._render(states, incoming_garbage)
        time.sleep(self._lock_delay * 0.5)

    def on_garbage_applied(
        self,
        player: str,
        lines: int,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        self._status.set_player(player, f"Garbage +{lines}")
        self._render(states, incoming_garbage)
        time.sleep(self._lock_delay * 0.5)

    def on_game_ended(
        self,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        status: str,
        winner: str | None,
        loser: str | None,
    ) -> None:
        self._status.end_battle(status=status, winner=winner, loser=loser)
        self._render(states, incoming_garbage)

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)
        self._set_statuses(f"Warning: {message}")

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
        self._set_statuses(f"Error: {message}")

    def _render(
        self,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        players: dict[str, _PlayerFrame] = {}
        for name, state in states.items():
            active = self._active.get(name)
            if active is None:
                active_piece = state.active.piece
                active_loc = (state.active.x, state.active.y, state.active.rotation)
            else:
                active_piece, active_loc = active
            players[name] = _PlayerFrame(
                name=name,
                board=make_board_frame(
                    state,
                    active_piece,
                    active_loc,
                    self._settings.visible_rows,
                    self._settings.queue_size,
                ),
                incoming_garbage=incoming_garbage[name],
                status=self._status.player(name),
            )

        with self._lock:
            self._frame = _RenderFrame(players=players)

    def _set_statuses(self, status: str) -> None:
        with self._lock:
            self._status.set_all_players(status)
            if self._frame is None:
                return
            players = {
                name: _PlayerFrame(
                    name=frame.name,
                    board=frame.board,
                    incoming_garbage=frame.incoming_garbage,
                    status=self._status.player(name),
                )
                for name, frame in self._frame.players.items()
            }
            self._frame = _RenderFrame(players=players)

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
            ui.add_css(CSS + _BATTLE_CSS)
            ui.query("body").classes("minorail-body")
            with ui.column().classes("minorail-shell minorail-battle-shell"):
                with ui.row().classes("minorail-topbar"):
                    ui.label("minorail").classes("minorail-title")
                    ui.label("battle web visualizer").classes("minorail-subtitle")
                boards: dict[str, Any] = {}
                sides: dict[str, Any] = {}
                with ui.row().classes("minorail-battle-main"):
                    for player in ("A", "B"):
                        with ui.column().classes("minorail-battle-player"):
                            with ui.column().classes("minorail-battle-player-content"):
                                ui.label(f"Player {player}").classes(
                                    "minorail-battle-player-title"
                                )
                                with ui.row().classes("minorail-battle-player-body"):
                                    boards[player] = ui.html(
                                        empty_board_html()
                                    ).classes("minorail-board-wrap")
                                    sides[player] = ui.html("").classes("minorail-side")

            def refresh() -> None:
                frame = visualizer._current_frame()
                if frame is None:
                    return
                for player in ("A", "B"):
                    player_frame = frame.players.get(player)
                    if player_frame is None:
                        continue
                    boards[player].set_content(board_html(player_frame.board))
                    sides[player].set_content(_player_side_html(player_frame))

            ui.timer(1 / 30, refresh, active=True)

        thread = threading.Thread(
            target=lambda: ui.run(
                host=self._host,
                port=self._port,
                title="minorail battle",
                reload=False,
                show=True,
                show_welcome_message=False,
            ),
            name="minorail-battle-web",
            daemon=True,
        )
        thread.start()
        self._server_started = True
        print(f"[info] battle web visualizer: {self.url}", file=sys.stderr)

    def _current_frame(self) -> Optional[_RenderFrame]:
        with self._lock:
            return self._frame

    def _wait_for_client(self) -> None:
        print("[info] waiting for battle web visualizer client", file=sys.stderr)
        if self._client_connected.wait(timeout=15):
            return
        raise RuntimeError(f"battle web visualizer did not open within 15s: {self.url}")


def _player_side_html(frame: _PlayerFrame) -> str:
    board = frame.board
    active = piece_preview(board.active_piece)
    hold = piece_preview(board.hold)
    queue = "".join(piece_preview(piece) for piece in board.queue)
    rotation = board.active_rotation.name if board.active_rotation is not None else ""
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
      <dl class="minorail-stats minorail-battle-stats">
        <div><dt>Combo</dt><dd>{board.combo}</dd></div>
        <div><dt>Back-to-Back</dt><dd>{board.back_to_back}</dd></div>
      </dl>
    </section>
    <section class="minorail-panel">
      <dl class="minorail-stats minorail-battle-garbage-stats">
        <div><dt>Incoming Garbage</dt><dd>{frame.incoming_garbage}</dd></div>
      </dl>
    </section>
    <section class="minorail-panel minorail-status">
      <div class="minorail-section-title">status</div>
      {html.escape(frame.status)}
    </section>
    """


_BATTLE_CSS = """
.minorail-battle-shell {
  width: min(1600px, calc(100vw - 32px));
}
.minorail-battle-main {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 28px;
  width: 100%;
}
.minorail-battle-player {
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  min-width: 0;
}
.minorail-battle-player:nth-child(2) {
  align-items: flex-end;
}
.minorail-battle-player-content {
  align-items: flex-start;
  gap: 10px;
  width: fit-content;
  max-width: 100%;
}
.minorail-battle-player-title {
  color: #f8fafc;
  font-size: 15px;
  line-height: 20px;
  font-weight: 650;
}
.minorail-battle-player-body {
  align-items: flex-start;
  gap: 12px;
  flex-wrap: nowrap;
  width: fit-content;
  max-width: 100%;
}
.minorail-battle-player:nth-child(2) .minorail-battle-player-body {
  justify-content: flex-end;
}
.minorail-battle-player .minorail-board-wrap {
  flex: 0 0 auto;
  width: fit-content;
}
.minorail-battle-player .minorail-side {
  flex: 0 1 340px;
  min-width: 260px;
  max-width: 340px;
}
.minorail-battle-player .minorail-panel {
  width: 100%;
}
.minorail-battle-stats {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.minorail-battle-garbage-stats {
  grid-template-columns: minmax(0, 1fr);
}
@media (max-width: 1280px) {
  .minorail-battle-main {
    grid-template-columns: 1fr;
  }
  .minorail-battle-player:nth-child(2) {
    align-items: flex-start;
  }
  .minorail-battle-player-body {
    width: min(100%, 710px);
  }
  .minorail-battle-player:nth-child(2) .minorail-battle-player-body {
    justify-content: flex-start;
  }
}
@media (max-width: 720px) {
  .minorail-battle-shell {
    width: min(100vw - 20px, 440px);
  }
  .minorail-battle-player {
    width: 100%;
  }
  .minorail-battle-player-body {
    flex-wrap: wrap;
    width: 100%;
  }
  .minorail-battle-player .minorail-board-wrap {
    width: 100%;
  }
  .minorail-battle-player .minorail-side {
    max-width: none;
    min-width: 0;
    width: 100%;
  }
}
"""
