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
    entries: tuple[_PendingGarbage, ...] = ()
    last_hole: int | None = None

    @property
    def total(self) -> int:
        return sum(entry.lines for entry in self.entries)


class PptGarbageRules:
    """Puyo Puyo Tetris-style messy garbage based on public community notes.

    FOUR.lol credits Okey_Dokey for the observed PPT behavior: 90% chance to
    change holes after each insertion, and 30% chance after each line within an
    insertion. This is not an official Sega/Tetris Guideline specification.
    """

    MAX_RISE_PER_LOCK = 8
    WIDTH = 10
    ENTRY_HOLE_CHANGE_CHANCE = 0.9
    LINE_HOLE_CHANGE_CHANCE = 0.3

    def __init__(self, *, seed: int | None) -> None:
        self._rng = random.Random(seed)

    def empty_queue(self) -> GarbageQueue:
        return _GarbageQueue()

    def queue_total(self, queue: GarbageQueue) -> int:
        return _queue(queue).total

    def queue_chunks(self, queue: GarbageQueue) -> list[int]:
        return [entry.lines for entry in _queue(queue).entries]

    def exchange(self, *, attack: int, queue: GarbageQueue) -> GarbageExchange:
        current = _queue(queue)
        cancelled = min(max(0, attack), current.total)
        sent = max(0, attack - cancelled)
        queue_after = _consume_queue(
            current, cancelled, reroll_finished_entries=True, rng=self._rng
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
        entry = _PendingGarbage(lines=attack)
        return _GarbageQueue((*current.entries, entry), current.last_hole)

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

        holes, current = _holes_to_apply(current, lines, self._rng)
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


def _reroll_hole(rng: random.Random, current: int | None = None) -> int:
    if current is None:
        return rng.randrange(PptGarbageRules.WIDTH)
    hole = rng.randrange(PptGarbageRules.WIDTH - 1)
    if current is not None and hole >= current:
        hole += 1
    return hole


def _maybe_reroll_hole(
    rng: random.Random,
    current: int,
    *,
    chance: float,
) -> int:
    if rng.random() >= chance:
        return current
    return _reroll_hole(rng, current)


def _consume_queue(
    queue: _GarbageQueue,
    lines: int,
    *,
    reroll_finished_entries: bool,
    rng: random.Random,
) -> _GarbageQueue:
    remaining = max(0, lines)
    entries: list[_PendingGarbage] = []
    last_hole = queue.last_hole
    for entry in queue.entries:
        if remaining <= 0:
            entries.append(entry)
            continue
        if entry.lines <= remaining:
            remaining -= entry.lines
            if reroll_finished_entries and last_hole is not None:
                last_hole = _maybe_reroll_hole(
                    rng,
                    last_hole,
                    chance=PptGarbageRules.ENTRY_HOLE_CHANGE_CHANCE,
                )
            continue
        entries.append(_PendingGarbage(lines=entry.lines - remaining))
        remaining = 0
    return _GarbageQueue(tuple(entries), last_hole)


def _holes_to_apply(
    queue: _GarbageQueue,
    lines: int,
    rng: random.Random,
) -> tuple[list[int], _GarbageQueue]:
    holes: list[int] = []
    entries: list[_PendingGarbage] = []
    remaining = max(0, lines)
    last_hole = queue.last_hole
    for entry in queue.entries:
        if remaining <= 0:
            entries.append(entry)
            continue
        if last_hole is None:
            last_hole = _reroll_hole(rng)
        applied_lines = min(entry.lines, remaining)
        for _ in range(applied_lines):
            holes.append(last_hole)
            last_hole = _maybe_reroll_hole(
                rng,
                last_hole,
                chance=PptGarbageRules.LINE_HOLE_CHANGE_CHANCE,
            )
        remaining -= applied_lines
        if applied_lines == entry.lines:
            last_hole = _maybe_reroll_hole(
                rng,
                last_hole,
                chance=PptGarbageRules.ENTRY_HOLE_CHANGE_CHANCE,
            )
            continue
        entries.append(_PendingGarbage(lines=entry.lines - applied_lines))
    return holes, _GarbageQueue(tuple(entries), last_hole)


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
