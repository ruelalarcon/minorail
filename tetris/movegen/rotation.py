from __future__ import annotations

from typing import Optional

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation, rot_cw
from tetris.kicks.registry import kick_table
from tetris.movegen.collision import obstructed


def try_rotate(
    board: Board,
    piece: Piece,
    from_rot: Rotation,
    to_rot: Rotation,
    x: int,
    y: int,
    kickset: str,
) -> Optional[tuple[int, int, Rotation]]:
    for dx, dy in kick_table(kickset).kicks_between(piece, from_rot, to_rot):
        nx, ny = x + dx, y + dy
        if not obstructed(board, piece, to_rot, nx, ny):
            return (nx, ny, to_rot)
    return None


def try_rotate_180(
    board: Board,
    piece: Piece,
    from_rot: Rotation,
    x: int,
    y: int,
    kickset: str,
) -> Optional[tuple[int, int, Rotation]]:
    to_rot = rot_cw(rot_cw(from_rot))
    for dx, dy in kick_table(kickset).kicks_between(piece, from_rot, to_rot):
        nx, ny = x + dx, y + dy
        if not obstructed(board, piece, to_rot, nx, ny):
            return (nx, ny, to_rot)
    return None
