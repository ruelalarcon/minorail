from __future__ import annotations

from typing import Optional

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.pieces.cells import piece_cells
from suggestion.contracts.observed_snapshot import ObservedSnapshot


def moving_piece_for(
    snapshot: ObservedSnapshot, placement: Placement
) -> Optional[Piece]:
    placed = placement.location.piece
    active = snapshot.active.piece
    if placed == active:
        return active
    if not snapshot.can_hold:
        return None
    if snapshot.hold is None:
        if snapshot.queue and placed == snapshot.queue[0]:
            return snapshot.queue[0]
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
