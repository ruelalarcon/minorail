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
from visualizers.shared.terminal import (
    LiveTerminalRegion,
    board_width_columns,
    colored,
    pad_visible,
    render_board_lines,
    truncate_visible,
)
from visualizers.shared.status import VisualizerStatus

_BOARD_GAP = 8


class TerminalVisualizer:
    default_pathfinding = True

    def __init__(self, settings: VisualizerSettings) -> None:
        self._settings = settings
        self._move_delay = settings.move_delay_ms / 1000
        self._lock_delay = settings.lock_delay_ms / 1000
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
        out = _battle_lines(rendered[0], rendered[1], states["A"].board.width)
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
    lines = [title, *render_board_lines(state, visible_rows, active)]
    hold = colored(state.hold.value, state.hold) if state.hold else " "
    queue = " ".join(colored(p.value, p) for p in state.queue[:queue_size])
    active_text = active[0].value if active is not None else state.active.piece.value
    lines.extend(
        [
            f"Active: {colored(active_text, Piece(active_text))}",
            f"Hold: {hold}",
            f"Queue: {queue}",
            "",
            f"Combo: {state.combo}",
            f"Back-to-Back: {state.back_to_back}",
            f"Incoming Garbage: {incoming}",
            f"Status: {status}",
        ]
    )
    return lines


def _battle_lines(
    left_lines: list[str],
    right_lines: list[str],
    left_board_width: int,
) -> list[str]:
    left_region_width = max(len("Player A"), board_width_columns(left_board_width))
    left_region_width += _BOARD_GAP
    return [
        f"{pad_visible(truncate_visible(left, left_region_width), left_region_width)}{right}"
        for left, right in zip(left_lines, right_lines)
    ]
