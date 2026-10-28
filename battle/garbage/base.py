from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from collections.abc import Sequence

from tetris.game.state import GameState


# GarbageQueue is the rules-owned structured state waiting to rise on a board.
# incoming_garbage totals/chunks are public integer views reported externally.
GarbageQueue = Any


@dataclass(frozen=True)
class GarbageExchange:
    cancelled: int
    sent_packets: tuple[int, ...]
    queue_after: GarbageQueue

    @property
    def sent(self) -> int:
        return sum(self.sent_packets)


def cancel_packets(
    attacks: Sequence[int], available: int
) -> tuple[int, tuple[int, ...]]:
    """Offset oldest pending rows while retaining outgoing packet boundaries."""
    cancelled = 0
    sent = []
    for attack in attacks:
        count = min(attack, available)
        cancelled += count
        available -= count
        if attack > count:
            sent.append(attack - count)
    return cancelled, tuple(sent)


@dataclass(frozen=True)
class GarbageApplication:
    lines: int
    topped_out: bool
    queue_after: GarbageQueue


class GarbageRules(Protocol):
    def empty_queue(self) -> GarbageQueue: ...

    def queue_total(self, queue: GarbageQueue) -> int: ...

    def queue_chunks(self, queue: GarbageQueue) -> list[int]: ...

    def exchange(
        self,
        *,
        attacks: Sequence[int],
        queue: GarbageQueue,
        pieces_placed: int,
        sent_before: int,
    ) -> GarbageExchange: ...

    def enqueue_attack(self, queue: GarbageQueue, *, attack: int) -> GarbageQueue: ...

    def should_apply_on_lock(self, *, lines_cleared: int) -> bool: ...

    def apply_queue(
        self, state: GameState, queue: GarbageQueue
    ) -> GarbageApplication: ...
