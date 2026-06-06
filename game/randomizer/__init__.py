from __future__ import annotations

from typing import Any, Optional, Protocol

from core.piece import Piece
from game.randomizer.pure_random import PureRandom
from game.randomizer.seven_bag import SevenBag


class Randomizer(Protocol):
    def next(self) -> Piece: ...
    def peek_bag(self) -> list[Piece]: ...


def make_randomizer(
    rules_type: Optional[str], start_state: dict[str, Any]
) -> Optional[Randomizer]:
    match rules_type:
        case "seven_bag":
            bag_state = [Piece(p) for p in start_state.get("bag_state", [])]
            return SevenBag(bag_state=bag_state)
        case "pure_random":
            return PureRandom()
        case _:
            return None


__all__ = ["Randomizer", "SevenBag", "PureRandom", "make_randomizer"]
