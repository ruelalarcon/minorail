from __future__ import annotations

from typing import Optional, Protocol

from tetris.model.piece import Piece
from tetris.randomizer.pure_random import PureRandom
from tetris.randomizer.seven_bag import SevenBag


class Randomizer(Protocol):
    def next(self) -> Piece: ...
    def peek_bag(self) -> list[Piece]: ...


def make_randomizer(rules_type: Optional[str]) -> Optional[Randomizer]:
    match rules_type:
        case "seven_bag":
            return SevenBag()
        case "pure_random":
            return PureRandom()
        case _:
            return None


__all__ = ["Randomizer", "SevenBag", "PureRandom", "make_randomizer"]
