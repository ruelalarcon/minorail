from __future__ import annotations

from tetris.model.piece import Piece
from solo.runner.controls import GameControls
from tetris.model.rules import Rules
from tetris.game.state import GameState
from contracts.suggestion_result import SuggestionResult


class NullVisualizer:
    default_pathfinding = False

    def set_game_controls(self, controls: GameControls) -> None:
        pass

    def on_game_started(self, state: GameState) -> None:
        pass

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
        pass

    def on_top_out(self, state: GameState) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass
