from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from tetris.game.state import GameState


# GarbageQueue is the rules-owned structured state waiting to rise on a board.
# incoming_garbage is only the public integer view reported to UI/events/API.
GarbageQueue = Any


@dataclass(frozen=True)
class GarbageExchange:
    cancelled: int
    sent: int
    queue_after: GarbageQueue


@dataclass(frozen=True)
class GarbageApplication:
    lines: int
    topped_out: bool
    queue_after: GarbageQueue


class GarbageRules(Protocol):
    def empty_queue(self) -> GarbageQueue: ...

    def queue_total(self, queue: GarbageQueue) -> int: ...

    def exchange(self, *, attack: int, queue: GarbageQueue) -> GarbageExchange: ...

    def enqueue_attack(self, queue: GarbageQueue, *, attack: int) -> GarbageQueue: ...

    def should_apply_on_lock(self, *, lines_cleared: int) -> bool: ...

    def apply_queue(
        self, state: GameState, queue: GarbageQueue
    ) -> GarbageApplication: ...
