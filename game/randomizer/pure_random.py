from __future__ import annotations

import random

from core.piece import Piece

_ALL_PIECES = list(Piece)


class PureRandom:
    """Fully random randomizer — each piece is drawn independently."""

    def next(self) -> Piece:
        return random.choice(_ALL_PIECES)

    def peek_bag(self) -> list[Piece]:
        return []
