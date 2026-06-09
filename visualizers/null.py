from __future__ import annotations

from tetris.model.piece import Piece
from runner.visualizer_protocol import EngineControls
from tetris.model.rules import Rules
from tetris.game.state import GameState
from suggestion.contracts.suggestion_result import SuggestionResult


class NullVisualizer:
    def set_engine_controls(self, controls: EngineControls) -> None:
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

    def on_piece_locked(self, state: GameState) -> None:
        pass

    def on_top_out(self, state: GameState) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass
