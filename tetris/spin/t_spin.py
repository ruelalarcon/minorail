from __future__ import annotations

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.spin import Spin
from tetris.model.rotation import rotate_cell
from tetris.movegen.collision import obstructed


def detect_t_spin(
    location: PieceLocation,
    board: Board,
    *,
    rotated: bool,
    kick_index: int | None = None,
    force_mini: bool = False,
) -> Spin:
    if location.piece != Piece.T or not rotated:
        return Spin.none
    if not obstructed(
        board,
        location.piece,
        location.rotation,
        location.x,
        location.y - 1,
    ):
        return Spin.none

    corners = sum(
        1
        for cx, cy in ((-1, -1), (1, -1), (-1, 1), (1, 1))
        if board.occupied(location.x + cx, location.y + cy)
    )
    if corners < 3:
        return Spin.none
    if force_mini:
        return Spin.mini

    front_corners = (
        rotate_cell(location.rotation, -1, 1),
        rotate_cell(location.rotation, 1, 1),
    )
    front_occupied = sum(
        1
        for cx, cy in front_corners
        if board.occupied(location.x + cx, location.y + cy)
    )
    if front_occupied == 2 or kick_index == 4:
        return Spin.full
    return Spin.mini
