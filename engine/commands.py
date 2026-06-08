from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from game.state import GameState


@dataclass(frozen=True)
class CellEdit:
    x: int
    y: int
    filled: bool


@dataclass(frozen=True)
class EngineControls:
    set_cell: Callable[[int, int, bool], object]
    clear_board: Callable[[], object]
    get_state: Callable[[], GameState]
