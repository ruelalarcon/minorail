from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tetris.game.state import GameState


@dataclass(frozen=True)
class CellEdit:
    x: int
    y: int
    filled: bool


@dataclass(frozen=True)
class GameControls:
    set_cell: Callable[[int, int, bool], None]
    clear_board: Callable[[], None]
    get_state: Callable[[], GameState]
