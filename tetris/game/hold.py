from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tetris.model.piece import Piece
from tetris.model.placement import Placement


@dataclass(frozen=True)
class HoldResult:
    hold: Optional[Piece]
    queue: list[Piece]


class Hold:
    @staticmethod
    def infer_after_placement(
        *,
        active: Piece,
        hold: Optional[Piece],
        queue: list[Piece],
        placement: Placement,
        hold_used_this_turn: bool,
    ) -> HoldResult | None:
        placed = placement.location.piece
        next_hold = hold
        next_queue = list(queue)

        if placed == active:
            return HoldResult(hold=next_hold, queue=next_queue)

        if hold_used_this_turn:
            return None

        if hold is None:
            if not next_queue or placed != next_queue[0]:
                return None
            next_hold = active
            next_queue.pop(0)
            return HoldResult(hold=next_hold, queue=next_queue)

        if placed == hold:
            next_hold = active
            return HoldResult(hold=next_hold, queue=next_queue)

        return None
