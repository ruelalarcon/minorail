from __future__ import annotations

import random

from tetris.model.piece import Piece

_ALL_PIECES = list(Piece)


class PureRandom:
    """Fully random randomizer where each piece is drawn independently."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def next(self) -> Piece:
        return self._rng.choice(_ALL_PIECES)

    def peek_bag(self) -> list[Piece]:
        return []
