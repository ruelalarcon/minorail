from __future__ import annotations

from contracts.suggestion_result import SuggestionResult
from tetris.game.state import GameState
from tetris.model.piece import Piece
from tetris.model.rules import Rules


class NullVisualizer:
    default_pathfinding = False

    def on_game_started(
        self, states: dict[str, GameState], incoming_garbage: dict[str, int]
    ) -> None:
        pass

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
        *,
        attack: int,
    ) -> None:
        pass

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
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass
