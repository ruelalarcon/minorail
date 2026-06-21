from __future__ import annotations

import sys
import time

from tetris.model.piece import Piece
from solo.runner.controls import GameControls
from tetris.model.rules import Rules
from tetris.game.state import GameState
from contracts.suggestion_result import SuggestionResult


class HeadlessVisualizer:
    default_pathfinding = False

    def __init__(self, progress_every: int = 1000) -> None:
        self._progress_every = progress_every
        self._pieces = 0
        self._started_at = 0.0

    def set_game_controls(self, controls: GameControls) -> None:
        pass

    def on_game_started(self, state: GameState) -> None:
        self._pieces = 0
        self._started_at = time.time()

    def on_spawn(self, state: GameState, piece: Piece) -> None:
        pass

    def animate_suggestion(
        self,
        state: GameState,
        moving_piece: Piece,
        result: SuggestionResult,
        hold_used: bool,
        rules: Rules,
    ) -> None:
        pass

    def on_piece_locked(self, state: GameState, *, total_attack: int) -> None:
        self._pieces += 1
        if self._progress_every <= 0 or self._pieces % self._progress_every != 0:
            return

        elapsed = time.time() - self._started_at
        pps = self._pieces / elapsed if elapsed > 0 else 0
        print(
            f"[info] pieces={self._pieces} elapsed={elapsed:.1f}s pps={pps:.2f}",
            file=sys.stderr,
        )

    def on_top_out(self, state: GameState) -> None:
        pass

    def warning(self, message: str) -> None:
        print(f"[warn] {message}", file=sys.stderr)

    def error(self, message: str) -> None:
        print(f"[error] {message}", file=sys.stderr)
