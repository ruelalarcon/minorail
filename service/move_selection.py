from __future__ import annotations

from typing import Optional

from core.board import Board, piece_cells
from core.piece import Piece
from core.placement import Placement
from service.snapshot import ObservedSnapshot


def moving_piece_for(
    snapshot: ObservedSnapshot, placement: Placement
) -> Optional[Piece]:
    placed = placement.location.piece
    current = snapshot.current
    if current is None:
        return None
    if placed == current:
        return current
    if not snapshot.can_hold:
        return None
    if snapshot.hold is None:
        if len(snapshot.queue) >= 2 and placed == snapshot.queue[1]:
            return snapshot.queue[1]
        return None
    if placed == snapshot.hold:
        return snapshot.hold
    return None


def placement_fits(board: Board, placement: Placement) -> bool:
    loc = placement.location
    return all(
        0 <= x < 10 and 0 <= y < 40 and not board.occupied(x, y)
        for x, y in piece_cells(loc.piece, loc.rotation, loc.x, loc.y)
    )


def pick_move(
    moves: list[Placement], snapshot: ObservedSnapshot
) -> Optional[Placement]:
    for candidate in moves:
        if not placement_fits(snapshot.board, candidate):
            continue
        if moving_piece_for(snapshot, candidate) is not None:
            return candidate
    return None
