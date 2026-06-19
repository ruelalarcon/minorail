from __future__ import annotations

from tetris.game.state import GameState


def stack_height(state: GameState) -> int:
    return max((col.bit_length() for col in state.board.cols), default=0)


def occupied_cells(state: GameState) -> int:
    return sum(col.bit_count() for col in state.board.cols)
