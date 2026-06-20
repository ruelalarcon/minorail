from __future__ import annotations

import random
from dataclasses import dataclass

from battle.garbage.base import (
    GarbageApplication,
    GarbageExchange,
    GarbageQueue,
)
from tetris.game.state import GameState


@dataclass(frozen=True)
class _GarbagePacket:
    lines: int
    hole: int


@dataclass(frozen=True)
class _GarbageQueue:
    packets: tuple[_GarbagePacket, ...] = ()

    @property
    def total(self) -> int:
        return sum(packet.lines for packet in self.packets)


class GenericGarbageRules:
    MAX_RISE_PER_LOCK = 8

    def __init__(self, *, seed: int | None) -> None:
        self._rng = random.Random(seed)

    def empty_queue(self) -> GarbageQueue:
        return _GarbageQueue()

    def queue_total(self, queue: GarbageQueue) -> int:
        return _queue(queue).total

    def exchange(self, *, attack: int, queue: GarbageQueue) -> GarbageExchange:
        current = _queue(queue)
        cancelled = min(max(0, attack), current.total)
        sent = max(0, attack - cancelled)
        queue_after = _consume_queue(current, cancelled)
        return GarbageExchange(
            cancelled=cancelled,
            sent=sent,
            queue_after=queue_after,
        )

    def enqueue_attack(self, queue: GarbageQueue, *, attack: int) -> GarbageQueue:
        current = _queue(queue)
        if attack <= 0:
            return current
        packet = _GarbagePacket(lines=attack, hole=self._rng.randrange(10))
        return _GarbageQueue((*current.packets, packet))

    def should_apply_on_lock(self, *, lines_cleared: int) -> bool:
        return lines_cleared == 0

    def apply_queue(self, state: GameState, queue: GarbageQueue) -> GarbageApplication:
        current = _queue(queue)
        lines = min(current.total, self.MAX_RISE_PER_LOCK)
        if lines == 0:
            return GarbageApplication(
                lines=0,
                topped_out=False,
                queue_after=current,
            )

        holes = _holes_to_apply(current, lines)
        topped_out = _raise_garbage(state, holes)
        return GarbageApplication(
            lines=lines,
            topped_out=topped_out,
            queue_after=_consume_queue(current, lines),
        )


def _queue(value: GarbageQueue) -> _GarbageQueue:
    if not isinstance(value, _GarbageQueue):
        raise TypeError(f"expected _GarbageQueue, got {type(value).__name__}")
    return value


def _consume_queue(queue: _GarbageQueue, lines: int) -> _GarbageQueue:
    remaining = max(0, lines)
    packets: list[_GarbagePacket] = []
    for packet in queue.packets:
        if remaining <= 0:
            packets.append(packet)
            continue
        if packet.lines <= remaining:
            remaining -= packet.lines
            continue
        packets.append(_GarbagePacket(lines=packet.lines - remaining, hole=packet.hole))
        remaining = 0
    return _GarbageQueue(tuple(packets))


def _holes_to_apply(queue: _GarbageQueue, lines: int) -> list[int]:
    holes: list[int] = []
    remaining = max(0, lines)
    for packet in queue.packets:
        if remaining <= 0:
            break
        count = min(packet.lines, remaining)
        holes.extend([packet.hole] * count)
        remaining -= count
    return holes


def _raise_garbage(state: GameState, holes: list[int]) -> bool:
    lines = len(holes)
    mask40 = (1 << 40) - 1
    overflow_mask = ((1 << lines) - 1) << (40 - lines)
    topped_out = any(col & overflow_mask for col in state.board.cols)

    bottom_masks = [0] * 10
    for y, hole in enumerate(holes):
        for x in range(10):
            if x != hole:
                bottom_masks[x] |= 1 << y

    for x in range(10):
        state.board.cols[x] = ((state.board.cols[x] << lines) & mask40) | bottom_masks[
            x
        ]
    return topped_out
