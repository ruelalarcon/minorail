from __future__ import annotations

import random
from typing import Optional

from tetris.model.piece import Piece

_ALL_PIECES = list(Piece)


class SevenBag:
    """Standard 7-bag randomizer."""

    def __init__(self, bag_state: Optional[list[Piece]] = None):
        self._remaining: list[Piece] = list(bag_state) if bag_state is not None else []
        self._refill_if_empty()

    def _refill_if_empty(self) -> None:
        if not self._remaining:
            self._remaining = list(_ALL_PIECES)
            random.shuffle(self._remaining)

    def next(self) -> Piece:
        self._refill_if_empty()
        piece = self._remaining.pop(0)
        self._refill_if_empty()
        return piece

    def peek_bag(self) -> list[Piece]:
        return list(self._remaining)
