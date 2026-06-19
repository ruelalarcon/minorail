from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tetris.game.state import GameState


@dataclass(frozen=True)
class GarbageExchange:
    cancelled: int
    sent: int
    incoming_after: int


@dataclass(frozen=True)
class GarbageApplication:
    lines: int
    topped_out: bool


class GarbageRules(Protocol):
    def exchange(self, *, attack: int, incoming: int) -> GarbageExchange: ...

    def should_apply_on_lock(self, *, lines_cleared: int) -> bool: ...

    def apply_pending(self, state: GameState, pending: int) -> GarbageApplication: ...
