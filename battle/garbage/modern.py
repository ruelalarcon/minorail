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
class _GarbagePhase:
    min_locks: int
    line_hole_change_chance: float


@dataclass(frozen=True)
class _GarbageQueue:
    entries: tuple[_PendingGarbage, ...] = ()
    last_hole: int | None = None
    locks: int = 0

    @property
    def total(self) -> int:
        return sum(entry.lines for entry in self.entries)


class ModernGarbageRules:
    """Tetris Effect: Connected Zone Battle-inspired garbage.

    TetrisWiki describes Zone Battle garbage as three score phases: clean random
    columns before 20,000 points, slightly more random holes after 20,000, and
    very random holes after 60,000. Minorail's garbage interface does not carry
    score or Zone state, so this approximates those phases with per-player lock
    counts that reset through empty_queue() at each game boundary.
    """

    MAX_RISE_PER_LOCK = 8
    WIDTH = 10
    # Approximate score thresholds. At guideline scoring rates, 50 and 150
    # locks are practical mid-game and late-game stand-ins for 20k and 60k.
    PHASES = (
        _GarbagePhase(
            min_locks=0,
            line_hole_change_chance=0.0,
        ),
        _GarbagePhase(
            min_locks=50,
            line_hole_change_chance=0.18,
        ),
        _GarbagePhase(
            min_locks=150,
            line_hole_change_chance=0.70,
        ),
    )

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
        queue_after = _consume_queue(current, cancelled)
        return GarbageExchange(
            cancelled=cancelled,
            sent=sent,
            queue_after=_increment_locks(queue_after),
        )

    def enqueue_attack(self, queue: GarbageQueue, *, attack: int) -> GarbageQueue:
        current = _queue(queue)
        if attack <= 0:
            return current
        entry = _PendingGarbage(lines=attack)
        return _GarbageQueue(
            (*current.entries, entry), current.last_hole, current.locks
        )

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


def _phase_for_locks(locks: int) -> _GarbagePhase:
    phase = ModernGarbageRules.PHASES[0]
    for candidate in ModernGarbageRules.PHASES:
        if locks >= candidate.min_locks:
            phase = candidate
    return phase


def _increment_locks(queue: _GarbageQueue) -> _GarbageQueue:
    return _GarbageQueue(queue.entries, queue.last_hole, queue.locks + 1)


def _reroll_hole(rng: random.Random, current: int | None = None) -> int:
    if current is None:
        return rng.randrange(ModernGarbageRules.WIDTH)
    hole = rng.randrange(ModernGarbageRules.WIDTH - 1)
    if hole >= current:
        hole += 1
    return hole


def _maybe_reroll_hole(
    rng: random.Random,
    current: int,
    *,
    chance: float,
) -> int:
    if chance <= 0.0 or rng.random() >= chance:
        return current
    return _reroll_hole(rng, current)


def _consume_queue(queue: _GarbageQueue, lines: int) -> _GarbageQueue:
    remaining = max(0, lines)
    entries: list[_PendingGarbage] = []
    for entry in queue.entries:
        if remaining <= 0:
            entries.append(entry)
            continue
        if entry.lines <= remaining:
            remaining -= entry.lines
            continue
        entries.append(_PendingGarbage(lines=entry.lines - remaining))
        remaining = 0
    return _GarbageQueue(tuple(entries), queue.last_hole, queue.locks)


def _holes_to_apply(
    queue: _GarbageQueue,
    lines: int,
    rng: random.Random,
) -> tuple[list[int], _GarbageQueue]:
    phase = _phase_for_locks(queue.locks)
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
                chance=phase.line_hole_change_chance,
            )
        remaining -= applied_lines
        if applied_lines == entry.lines:
            # A completed attack chunk starts the next chunk in another random
            # clean column, matching the observed "random clean columns" start.
            last_hole = _reroll_hole(rng, last_hole)
            continue
        entries.append(_PendingGarbage(lines=entry.lines - applied_lines))
    return holes, _GarbageQueue(tuple(entries), last_hole, queue.locks)


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
