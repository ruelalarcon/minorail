from __future__ import annotations

import sys
import time
from typing import Any, Optional

from core.board import piece_cells
from core.piece import Piece
from core.rotation import Rotation
from game.rules import Rules
from game.state import GameState
from movegen.pathfinder import MoveStep, apply_step, obstructed
from service.snapshot import SuggestionResult

RESET = "\033[0m"
DIM = "\033[2m"

PIECE_COLORS = {
    Piece.I: "\033[96m",  # cyan
    Piece.O: "\033[93m",  # yellow
    Piece.T: "\033[95m",  # magenta
    Piece.L: "\033[33m",  # orange
    Piece.J: "\033[94m",  # blue
    Piece.S: "\033[92m",  # green
    Piece.Z: "\033[91m",  # red
}

FILLED = "[]"
EMPTY = "  "
GHOST = DIM + "\xb7\xb7" + RESET


class TerminalVisualizer:
    def __init__(self, settings: dict[str, Any]) -> None:
        self._settings = settings
        cfg = self._settings["visualizer"]
        self._move_delay = cfg["move_delay_ms"] / 1000
        self._lock_delay = cfg["lock_delay_ms"] / 1000
        self._first_move_delay = cfg["first_move_delay_ms"] / 1000
        self._first_spawn = True

    def on_game_started(self, state: GameState) -> None:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    def on_spawn(self, state: GameState, piece: Piece) -> None:
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
            self._render(state, moving_piece, (ax, ay, arot))
        else:
            self.warning(result.reason or "no path found")
            placement = result.placement
            if placement is not None:
                loc = placement.location
                self._render(state, moving_piece, (loc.x, loc.y, loc.rotation))

        time.sleep(self._lock_delay)

    def on_piece_locked(self, state: GameState) -> None:
        self._render(state)
        time.sleep(self._lock_delay * 0.5)

    def on_top_out(self, state: GameState) -> None:
        self._render(state)

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)

    def _render(
        self,
        state: GameState,
        active_piece: Optional[Piece] = None,
        active_loc: Optional[tuple[int, int, Rotation]] = None,
    ) -> None:
        if active_piece is None or active_loc is None:
            active_piece = state.active.piece
            active_loc = (state.active.x, state.active.y, state.active.rotation)
        cfg = self._settings["visualizer"]
        _render(
            state,
            active_piece,
            active_loc,
            cfg["visible_rows"],
            cfg["queue_size"],
        )


def _colored(text: str, piece: Piece) -> str:
    return PIECE_COLORS[piece] + text + RESET


def _render(
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    visible_rows: int,
    queue_size: int,
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
                grid[ay][ax] = _colored(FILLED, active_piece)

    board_lines: list[str] = ["+" + "--" * 10 + "+"]
    for row in reversed(range(visible_rows)):
        cells = "".join(EMPTY if c == unset else c for c in grid[row])
        board_lines.append("|" + cells + "|")
    board_lines.append("+" + "--" * 10 + "+")

    if active_piece is not None and active_loc is not None:
        active_x, active_y, active_rotation = active_loc
        active_str = _colored(active_piece.value, active_piece)
        active_side = [
            f"Active Piece: {active_str}",
            f"X: {active_x}",
            f"Y: {active_y}",
            f"Orientation: {active_rotation.name}",
            "",
        ]
    else:
        active_side = []

    hold_str = _colored(state.hold.value, state.hold) if state.hold else " "
    next_str = " ".join(_colored(p.value, p) for p in state.queue[:queue_size])
    side: list[str] = active_side + [
        f"Hold: {hold_str}",
        f"Queue: {next_str}",
        "",
        f"Combo: {state.combo}",
        f"Back-to-Back: {state.back_to_back}",
    ]

    out: list[str] = []
    for i, row_str in enumerate(board_lines):
        out.append(f"{row_str}  {side[i] if i < len(side) else ''}")

    sys.stdout.write("\033[H")
    sys.stdout.write("\n".join(f"{line}\033[K" for line in out) + "\n")
    sys.stdout.flush()
