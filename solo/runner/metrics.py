from __future__ import annotations

from tetris.game.state import GameState


def stack_height(state: GameState) -> int:
    return state.board.stack_height()


def occupied_cells(state: GameState) -> int:
    return state.board.occupied_count()
