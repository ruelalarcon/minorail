from __future__ import annotations

import sys
import time

from contracts.suggestion_result import SuggestionResult
from settings import VisualizerSettings
from solo.visualizers.terminal import EMPTY, FILLED, GHOST, PIECE_COLORS, RESET
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.movegen.pathfinder import MoveStep, apply_step, obstructed
from tetris.pieces.cells import piece_cells


class TerminalVisualizer:
    default_pathfinding = True

    def __init__(self, settings: VisualizerSettings) -> None:
        self._settings = settings
        self._move_delay = settings.move_delay_ms / 1000
        self._lock_delay = settings.lock_delay_ms / 1000
        self._first_move_delay = settings.first_move_delay_ms / 1000
        self._first_spawn = True
        self._status = "Battle"
        self._active: dict[str, tuple[Piece, tuple[int, int, Rotation]] | None] = {
            "A": None,
            "B": None,
        }

    def on_game_started(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        self._status = "Battle started"
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        self._render(states, incoming_garbage)

    def on_spawn(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        piece: Piece,
    ) -> None:
        state = states[player]
        self._status = f"{player} spawn: {piece.value}"
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
            self._status = f"{player} hold"
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
                self._status = f"{player} move: {step.value}"
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
            self._status = f"{player} move: {MoveStep.HardDrop.value}"
            self._active[player] = (moving_piece, (ax, ay, arot))
        elif result.placement is not None:
            loc = result.placement.location
            self._status = f"{player}: {result.reason or 'Placement selected'}"
            self._active[player] = (moving_piece, (loc.x, loc.y, loc.rotation))

        self._render(states, incoming_garbage)
        time.sleep(self._lock_delay)

    def on_piece_locked(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        self._status = f"{player} locked"
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
        self._status = f"{player} garbage +{lines}"
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
        self._status = f"Ended: {status} winner={winner} loser={loser}"
        self._render(states, incoming_garbage)

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)
        self._status = f"Warning: {message}"

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
        self._status = f"Error: {message}"

    def _render(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        rendered = [
            _board_lines(
                "Player A",
                states["A"],
                incoming_garbage["A"],
                self._active.get("A"),
                self._settings.visible_rows,
                self._settings.queue_size,
            ),
            _board_lines(
                "Player B",
                states["B"],
                incoming_garbage["B"],
                self._active.get("B"),
                self._settings.visible_rows,
                self._settings.queue_size,
            ),
        ]
        width = max(len(_strip_ansi(line)) for line in rendered[0])
        out = [
            f"{left:<{width + _ansi_extra(left)}}    {right}"
            for left, right in zip(*rendered)
        ]
        out.append("")
        out.append(f"Status: {self._status}")
        sys.stdout.write("\033[H")
        sys.stdout.write("\n".join(f"{line}\033[K" for line in out) + "\n")
        sys.stdout.flush()


def _board_lines(
    title: str,
    state: GameState,
    incoming: int,
    active: tuple[Piece, tuple[int, int, Rotation]] | None,
    visible_rows: int,
    queue_size: int,
) -> list[str]:
    unset = "\x00"
    grid: list[list[str]] = [[unset for _ in range(10)] for _ in range(visible_rows)]
    for x in range(10):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                grid[y][x] = FILLED

    if active is not None:
        active_piece, active_loc = active
        px, py, prot = active_loc
        drop = state.board.drop_distance(active_piece, prot, px, py)
        for gx, gy in piece_cells(active_piece, prot, px, py - drop):
            if 0 <= gx < 10 and 0 <= gy < visible_rows and grid[gy][gx] == unset:
                grid[gy][gx] = GHOST
        for ax, ay in piece_cells(active_piece, prot, px, py):
            if 0 <= ax < 10 and 0 <= ay < visible_rows:
                grid[ay][ax] = _colored(FILLED, active_piece)

    lines = [title, "+" + "--" * 10 + "+"]
    for row in reversed(range(visible_rows)):
        cells = "".join(EMPTY if c == unset else c for c in grid[row])
        lines.append("|" + cells + "|")
    lines.append("+" + "--" * 10 + "+")
    hold = _colored(state.hold.value, state.hold) if state.hold else " "
    queue = " ".join(_colored(p.value, p) for p in state.queue[:queue_size])
    active_text = active[0].value if active is not None else state.active.piece.value
    lines.extend(
        [
            f"Active: {_colored(active_text, Piece(active_text))}",
            f"Hold: {hold}",
            f"Queue: {queue}",
            f"Combo: {state.combo}",
            f"Back-to-Back: {state.back_to_back}",
            f"Incoming Garbage: {incoming}",
        ]
    )
    return lines


def _colored(text: str, piece: Piece) -> str:
    return PIECE_COLORS[piece] + text + RESET


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
