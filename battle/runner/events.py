from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tetris.game.state import AppliedMove
from tetris.model.placement import Placement


@dataclass(frozen=True)
class GameStartedEvent:
    session_id: str
    seed: int | None
    players: tuple[str, str]


@dataclass(frozen=True)
class PieceLockedEvent:
    session_id: str
    player: str
    piece_index: int
    placement: Placement
    hold_used: bool
    applied: AppliedMove
    stack_height: int
    occupied_cells: int
    attack: int
    incoming_garbage_before: int
    garbage_cancelled: int
    garbage_sent: int
    incoming_garbage_after: int


@dataclass(frozen=True)
class GarbageAppliedEvent:
    session_id: str
    player: str
    lines: int
    incoming_garbage_after: int
    stack_height: int
    occupied_cells: int


@dataclass(frozen=True)
class GameEndedEvent:
    session_id: str
    status: str
    winner: str | None
    loser: str | None
    pieces: dict[str, int]
    elapsed: float
    pps: float
    stack_height: dict[str, int]
    occupied_cells: dict[str, int]
    incoming_garbage: dict[str, int]


class RunObserver(Protocol):
    def on_game_started(self, event: GameStartedEvent) -> None: ...

    def on_piece_locked(self, event: PieceLockedEvent) -> None: ...

    def on_garbage_applied(self, event: GarbageAppliedEvent) -> None: ...

    def on_game_ended(self, event: GameEndedEvent) -> None: ...
