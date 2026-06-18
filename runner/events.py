from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tetris.game.state import AppliedMove
from tetris.model.placement import Placement


@dataclass(frozen=True)
class GameStartedEvent:
    session_id: str
    seed: int | None


@dataclass(frozen=True)
class PieceLockedEvent:
    session_id: str
    piece_index: int
    placement: Placement
    hold_used: bool
    applied: AppliedMove
    stack_height: int
    occupied_cells: int


@dataclass(frozen=True)
class GameEndedEvent:
    session_id: str
    status: str
    pieces: int
    elapsed: float
    pps: float
    stack_height: int
    occupied_cells: int


class RunObserver(Protocol):
    def on_game_started(self, event: GameStartedEvent) -> None: ...

    def on_piece_locked(self, event: PieceLockedEvent) -> None: ...

    def on_game_ended(self, event: GameEndedEvent) -> None: ...
