from __future__ import annotations

import random

from battle.garbage.base import GarbageApplication, GarbageExchange
from tetris.game.state import GameState


class GenericGarbageRules:
    MAX_RISE_PER_LOCK = 8

    def __init__(self, *, seed: int | None) -> None:
        self._rng = random.Random(seed)

    def exchange(self, *, attack: int, incoming: int) -> GarbageExchange:
        cancelled = min(max(0, attack), max(0, incoming))
        sent = max(0, attack - cancelled)
        incoming_after = max(0, incoming - cancelled)
        return GarbageExchange(
            cancelled=cancelled,
            sent=sent,
            incoming_after=incoming_after,
        )

    def should_apply_on_lock(self, *, lines_cleared: int) -> bool:
        return lines_cleared == 0

    def apply_pending(self, state: GameState, pending: int) -> GarbageApplication:
        lines = min(max(0, pending), self.MAX_RISE_PER_LOCK)
        if lines == 0:
            return GarbageApplication(lines=0, topped_out=False)

        holes = [self._rng.randrange(10) for _ in range(lines)]
        topped_out = _raise_garbage(state, holes)
        return GarbageApplication(lines=lines, topped_out=topped_out)


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
