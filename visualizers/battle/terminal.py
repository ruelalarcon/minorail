from __future__ import annotations

import sys
import time

from contracts.suggestion_result import SuggestionResult
from settings import VisualizerSettings
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
        self._status = VisualizerStatus(("A", "B"))
        self._active: dict[str, tuple[Piece, tuple[int, int, Rotation]] | None] = {
            "A": None,
            "B": None,
        }
        self._terminal = LiveTerminalRegion()

    def on_game_started(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        self._status.reset_players("Battle started")
        self._terminal.start(self._frame_height())
        self._render(states, incoming_garbage)

    def on_spawn(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        piece: Piece,
    ) -> None:
        state = states[player]
        self._status.set_player(player, f"Spawn: {piece.value}")
        self._active[player] = (piece, (state.active.x, state.active.y, Rotation.North))
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
            self._status.set_player(player, "Hold")
            self._active[player] = (
                moving_piece,
                (state.active.x, state.active.y, Rotation.North),
            )
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
                self._status.set_player(player, f"Move: {step.value}")
                self._active[player] = (moving_piece, (ax, ay, arot))
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
            self._status.set_player(player, f"Move: {MoveStep.HardDrop.value}")
            self._active[player] = (moving_piece, (ax, ay, arot))
        elif result.placement is not None:
            loc = result.placement.location
            self._status.set_player(player, result.reason or "Placement selected")
            self._active[player] = (moving_piece, (loc.x, loc.y, loc.rotation))

        self._render(states, incoming_garbage)
        time.sleep(self._lock_delay)

    def on_piece_locked(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        self._status.set_player(player, "Locked")
        self._active[player] = None
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
        self._status.set_all_players(f"Warning: {message}")

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
        self._status.set_all_players(f"Error: {message}")

    def _render(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        rendered = [
            _board_lines(
                "Player A",
                states["A"],
                incoming_garbage["A"],
                self._active.get("A"),
                self._status.player("A"),
                self._settings.visible_rows,
                self._settings.queue_size,
            ),
            _board_lines(
                "Player B",
                states["B"],
                incoming_garbage["B"],
                self._active.get("B"),
                self._status.player("B"),
                self._settings.visible_rows,
                self._settings.queue_size,
            ),
        ]
        width = max(len(_strip_ansi(line)) for line in rendered[0])
        out = [
            f"{left:<{width + _ansi_extra(left)}}    {right}"
            for left, right in zip(*rendered)
        ]
        self._terminal.render(out)

    def _frame_height(self) -> int:
        return self._settings.visible_rows + 12


def _board_lines(
    title: str,
    state: GameState,
    incoming: int,
    active: tuple[Piece, tuple[int, int, Rotation]] | None,
    status: str,
    visible_rows: int,
    queue_size: int,
) -> list[str]:
    unset = "\x00"
    width = state.board.width
    visible_rows = min(visible_rows, state.board.height)
    grid: list[list[str]] = [[unset for _ in range(width)] for _ in range(visible_rows)]
    for x in range(width):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                grid[y][x] = FILLED

    if active is not None:
        active_piece, active_loc = active
        px, py, prot = active_loc
        drop = state.board.drop_distance(active_piece, prot, px, py)
        for gx, gy in piece_cells(active_piece, prot, px, py - drop):
            if 0 <= gx < width and 0 <= gy < visible_rows and grid[gy][gx] == unset:
                grid[gy][gx] = GHOST
        for ax, ay in piece_cells(active_piece, prot, px, py):
            if 0 <= ax < width and 0 <= ay < visible_rows:
                grid[ay][ax] = colored(FILLED, active_piece)

    lines = [title, "+" + "--" * width + "+"]
    for row in reversed(range(visible_rows)):
        cells = "".join(EMPTY if c == unset else c for c in grid[row])
        lines.append("|" + cells + "|")
    lines.append("+" + "--" * width + "+")
    hold = colored(state.hold.value, state.hold) if state.hold else " "
    queue = " ".join(colored(p.value, p) for p in state.queue[:queue_size])
    active_text = active[0].value if active is not None else state.active.piece.value
    lines.extend(
        [
            f"Active: {colored(active_text, Piece(active_text))}",
            f"Hold: {hold}",
            f"Queue: {queue}",
            f"Combo: {state.combo}",
            f"Back-to-Back: {state.back_to_back}",
            f"Incoming Garbage: {incoming}",
            "",
            "Status:",
            status,
        ]
    )
    return lines


def _strip_ansi(value: str) -> str:
    result = ""
    in_escape = False
    for char in value:
        if char == "\033":
            in_escape = True
        elif in_escape and char == "m":
            in_escape = False
        elif not in_escape:
            result += char
    return result


def _ansi_extra(value: str) -> int:
    return len(value) - len(_strip_ansi(value))
