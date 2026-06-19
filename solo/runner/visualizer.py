from __future__ import annotations

from typing import Protocol

from solo.runner.controls import GameControls
from contracts.suggestion_result import SuggestionResult
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rules import Rules


class SoloVisualizer(Protocol):
    default_pathfinding: bool

    def on_game_started(self, state: GameState) -> None: ...

    def on_spawn(self, state: GameState, piece: Piece) -> None: ...

    def animate_suggestion(
        self,
        state: GameState,
        moving_piece: Piece,
        result: SuggestionResult,
        hold_used: bool,
        rules: Rules,
    ) -> None: ...

    def on_piece_locked(self, state: GameState) -> None: ...

    def on_top_out(self, state: GameState) -> None: ...

    def warning(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...

    def set_game_controls(self, controls: GameControls) -> None: ...
