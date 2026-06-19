from __future__ import annotations

import sys
import time

from contracts.suggestion_result import SuggestionResult
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rules import Rules


class HeadlessBattleVisualizer:
    default_pathfinding = False

    def __init__(self, progress_every: int = 1000) -> None:
        self._progress_every = progress_every
        self._pieces = 0
        self._started_at = 0.0

    def on_game_started(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        self._pieces = 0
        self._started_at = time.time()

    def on_spawn(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        piece: Piece,
    ) -> None:
        pass

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
        pass

    def on_piece_locked(
        self,
        player: str,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        self._pieces += 1
        if self._progress_every <= 0 or self._pieces % self._progress_every != 0:
            return
        elapsed = time.time() - self._started_at
        pps = self._pieces / elapsed if elapsed > 0 else 0
        print(
            f"[info] locks={self._pieces} elapsed={elapsed:.1f}s "
            f"pps={pps:.2f} incoming={incoming_garbage}",
            file=sys.stderr,
        )

    def on_garbage_applied(
        self,
        player: str,
        lines: int,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
    ) -> None:
        pass

    def on_game_ended(
        self,
        states: dict[str, GameState],
        incoming_garbage: dict[str, int],
        status: str,
        winner: str | None,
        loser: str | None,
    ) -> None:
        print(
            f"[info] battle status={status} winner={winner} loser={loser} "
            f"incoming={incoming_garbage}",
            file=sys.stderr,
        )

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
