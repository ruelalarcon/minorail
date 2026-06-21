from __future__ import annotations

import sys
import time
from typing import Optional

from contracts.suggestion_result import SuggestionResult
from settings import VisualizerSettings
from solo.runner.controls import GameControls
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.movegen.pathfinder import MoveStep, apply_step, obstructed
from tetris.pieces.cells import piece_cells
from visualizers.shared.terminal import (
    EMPTY,
    FILLED,
    GHOST,
    LiveTerminalRegion,
    colored,
)
from visualizers.shared.status import VisualizerStatus


class TerminalVisualizer:
    default_pathfinding = True

    def __init__(self, settings: VisualizerSettings) -> None:
        self._settings = settings
        self._move_delay = settings.move_delay_ms / 1000
        self._lock_delay = settings.lock_delay_ms / 1000
        self._first_move_delay = settings.first_move_delay_ms / 1000
        self._first_spawn = True
        self._status = VisualizerStatus()
        self._terminal = LiveTerminalRegion()
        self._total_attack = 0

    def set_game_controls(self, controls: GameControls) -> None:
        pass

    def on_game_started(self, state: GameState) -> None:
        self._total_attack = 0
        self._status.set("Game started")
        self._terminal.start(self._frame_height())

    def on_spawn(self, state: GameState, piece: Piece) -> None:
        self._status.set(f"Spawn: {piece.value}")
        self._render(
            state,
            state.active.piece,
            (state.active.x, state.active.y, state.active.rotation),
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
            self._status.set("Hold")
            self._render(
                state, moving_piece, (state.active.x, state.active.y, Rotation.North)
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
                self._status.set(f"Move: {step.value}")
                self._render(state, moving_piece, (ax, ay, arot))
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
            self._status.set(f"Move: {MoveStep.HardDrop.value}")
            self._render(state, moving_piece, (ax, ay, arot))
        else:
            placement = result.placement
            if placement is not None:
                loc = placement.location
                self._status.set(result.reason or "Placement selected")
                self._render(state, moving_piece, (loc.x, loc.y, loc.rotation))

        time.sleep(self._lock_delay)

    def on_piece_locked(self, state: GameState, *, total_attack: int) -> None:
        self._total_attack = total_attack
        self._status.set("Locked")
        self._render(state)
        time.sleep(self._lock_delay * 0.5)

    def on_top_out(self, state: GameState) -> None:
        self._status.set("Top out")
        self._render(state)

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)
        self._status.set(f"Warning: {message}")

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
        self._status.set(f"Error: {message}")

    def _render(
        self,
        state: GameState,
        active_piece: Optional[Piece] = None,
        active_loc: Optional[tuple[int, int, Rotation]] = None,
    ) -> None:
        if active_piece is None or active_loc is None:
            active_piece = state.active.piece
            active_loc = (state.active.x, state.active.y, state.active.rotation)
        _render(
            state,
            active_piece,
            active_loc,
            self._settings.visible_rows,
            self._settings.queue_size,
            self._status.text,
            self._total_attack,
            self._terminal,
        )

    def _frame_height(self) -> int:
        return self._settings.visible_rows + 2


def _render(
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    visible_rows: int,
    queue_size: int,
    status: str,
    total_attack: int,
    terminal: LiveTerminalRegion,
) -> None:
    unset = "\x00"
    grid: list[list[str]] = [[unset for _ in range(10)] for _ in range(visible_rows)]

    for x in range(10):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                grid[y][x] = FILLED

    if active_piece is not None and active_loc is not None:
        px, py, prot = active_loc
        drop = state.board.drop_distance(active_piece, prot, px, py)
        for gx, gy in piece_cells(active_piece, prot, px, py - drop):
            if 0 <= gx < 10 and 0 <= gy < visible_rows and grid[gy][gx] == unset:
                grid[gy][gx] = GHOST
        for ax, ay in piece_cells(active_piece, prot, px, py):
            if 0 <= ax < 10 and 0 <= ay < visible_rows:
                grid[ay][ax] = colored(FILLED, active_piece)

    board_lines: list[str] = ["+" + "--" * 10 + "+"]
    for row in reversed(range(visible_rows)):
        cells = "".join(EMPTY if c == unset else c for c in grid[row])
        board_lines.append("|" + cells + "|")
    board_lines.append("+" + "--" * 10 + "+")

    if active_piece is not None and active_loc is not None:
        active_x, active_y, active_rotation = active_loc
        active_str = colored(active_piece.value, active_piece)
        active_side = [
            f"Active Piece: {active_str}",
            f"X: {active_x}",
            f"Y: {active_y}",
            f"Orientation: {active_rotation.name}",
            "",
        ]
    else:
        active_side = []

    hold_str = colored(state.hold.value, state.hold) if state.hold else " "
    next_str = " ".join(colored(p.value, p) for p in state.queue[:queue_size])
    side: list[str] = active_side + [
        f"Hold: {hold_str}",
        f"Queue: {next_str}",
        "",
        f"Combo: {state.combo}",
        f"Back-to-Back: {state.back_to_back}",
        "",
        f"Total Attack: {total_attack}",
        "",
        "Status:",
        status,
    ]

    out: list[str] = []
    for i, row_str in enumerate(board_lines):
        out.append(f"{row_str}  {side[i] if i < len(side) else ''}")

    terminal.render(out)
