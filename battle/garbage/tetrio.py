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
class _PendingGarbage:
    lines: int


@dataclass(frozen=True)
class _GarbageQueue:
    chunks: tuple[_PendingGarbage, ...] = ()
    last_hole: int | None = None

    @property
    def total(self) -> int:
        return sum(chunk.lines for chunk in self.chunks)


class TetrioGarbageRules:
    MAX_RISE_PER_LOCK = 8
    DEFAULT_WIDTH = 10

    def __init__(self, *, seed: int | None) -> None:
        self._rng = random.Random(seed)

    def empty_queue(self) -> GarbageQueue:
        return _GarbageQueue()

    def queue_total(self, queue: GarbageQueue) -> int:
        return _queue(queue).total

    def queue_chunks(self, queue: GarbageQueue) -> list[int]:
        return [chunk.lines for chunk in _queue(queue).chunks]

    def exchange(self, *, attack: int, queue: GarbageQueue) -> GarbageExchange:
        current = _queue(queue)
        cancelled = min(max(0, attack), current.total)
        sent = max(0, attack - cancelled)
        queue_after = _consume_queue(
            current, cancelled, reroll_finished_chunks=True, rng=self._rng
        )
        return GarbageExchange(
            cancelled=cancelled,
            sent=sent,
            queue_after=queue_after,
        )

    def enqueue_attack(self, queue: GarbageQueue, *, attack: int) -> GarbageQueue:
        current = _queue(queue)
        if attack <= 0:
            return current
        chunk = _PendingGarbage(lines=attack)
        return _GarbageQueue((*current.chunks, chunk), current.last_hole)

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

        holes, current = _holes_to_apply(current, lines, state.board.width, self._rng)
        topped_out = _raise_garbage(state, holes)
        return GarbageApplication(
            lines=lines,
            topped_out=topped_out,
            queue_after=current,
        )


def _queue(value: GarbageQueue) -> _GarbageQueue:
    if not isinstance(value, _GarbageQueue):
        raise TypeError(f"expected _GarbageQueue, got {type(value).__name__}")
    return value


def _reroll_hole(
    rng: random.Random, width: int = TetrioGarbageRules.DEFAULT_WIDTH
) -> int:
    return rng.randrange(width)


def _consume_queue(
    queue: _GarbageQueue,
    lines: int,
    *,
    reroll_finished_chunks: bool,
    rng: random.Random,
) -> _GarbageQueue:
    remaining = max(0, lines)
    chunks: list[_PendingGarbage] = []
    last_hole = queue.last_hole
    for chunk in queue.chunks:
        if remaining <= 0:
            chunks.append(chunk)
            continue
        if chunk.lines <= remaining:
            remaining -= chunk.lines
            if reroll_finished_chunks:
                last_hole = _reroll_hole(rng)
            continue
        chunks.append(_PendingGarbage(lines=chunk.lines - remaining))
        remaining = 0
    return _GarbageQueue(tuple(chunks), last_hole)


def _holes_to_apply(
    queue: _GarbageQueue,
    lines: int,
    width: int,
    rng: random.Random,
) -> tuple[list[int], _GarbageQueue]:
    holes: list[int] = []
    current = queue
    remaining = max(0, lines)
    for chunk in queue.chunks:
        if remaining <= 0:
            break
        if current.last_hole is None or current.last_hole >= width:
            current = _GarbageQueue(current.chunks, _reroll_hole(rng, width))
        assert current.last_hole is not None
        count = min(chunk.lines, remaining)
        holes.extend([current.last_hole] * count)
        current = _consume_queue(
            current,
            count,
            reroll_finished_chunks=chunk.lines <= count,
            rng=rng,
        )
        remaining -= count
    return holes, current


def _raise_garbage(state: GameState, holes: list[int]) -> bool:
    lines = len(holes)
    width = state.board.width
    height = state.board.height
    mask = (1 << height) - 1
    overflow_mask = ((1 << min(lines, height)) - 1) << max(0, height - lines)
    topped_out = any(col & overflow_mask for col in state.board.cols)

    bottom_masks = [0] * width
    for y, hole in enumerate(holes):
        if y >= height:
            break
        for x in range(width):
            if x != hole:
                bottom_masks[x] |= 1 << y

    for x in range(width):
        state.board.cols[x] = ((state.board.cols[x] << lines) & mask) | bottom_masks[x]
    return topped_out
