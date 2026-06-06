from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Optional

from core.board import Board, piece_cells
from core.location import PieceLocation
from core.piece import Piece
from core.rotation import Rotation, rot_ccw, rot_cw
from movegen.kicks import srs_kicks


class MoveStep(Enum):
    Left = "left"
    Right = "right"
    RotCW = "rot_cw"
    RotCCW = "rot_ccw"
    SoftDrop = "soft_drop"
    HardDrop = "hard_drop"


def obstructed(board: Board, piece: Piece, rotation: Rotation, x: int, y: int) -> bool:
    for cx, cy in piece_cells(piece, rotation, x, y):
        if cx < 0 or cx >= 10 or cy < 0:
            return True
        if cy < 40 and board.occupied(cx, cy):
            return True
    return False


def try_rotate(
    board: Board, piece: Piece, from_rot: Rotation, to_rot: Rotation, x: int, y: int
) -> Optional[tuple[int, int, Rotation]]:
    if piece == Piece.O:
        return None
    for dx, dy in srs_kicks(piece, from_rot, to_rot):
        nx, ny = x + dx, y + dy
        if not obstructed(board, piece, to_rot, nx, ny):
            return (nx, ny, to_rot)
    return None


def find_path(
    board: Board, piece: Piece, target: PieceLocation
) -> Optional[list[MoveStep]]:
    """
    BFS from spawn (North, x=4, y=19) to the target placement.
    Returns the move sequence ending with HardDrop, or None if unreachable.
    """
    spawn_x, spawn_y, spawn_rot = 4, 19, Rotation.North
    if obstructed(board, piece, spawn_rot, spawn_x, spawn_y):
        spawn_y = 20
        if obstructed(board, piece, spawn_rot, spawn_x, spawn_y):
            return None

    # State = tuple[int, int, Rotation]
    start = (spawn_x, spawn_y, spawn_rot)
    parent: dict[
        tuple[int, int, Rotation], tuple[tuple[int, int, Rotation], MoveStep]
    ] = {
        start: (start, MoveStep.HardDrop)  # sentinel for start
    }
    queue: deque[tuple[int, int, Rotation]] = deque([start])

    def enqueue(
        state: tuple[int, int, Rotation],
        prev: tuple[int, int, Rotation],
        step: MoveStep,
    ) -> None:
        if state not in parent:
            parent[state] = (prev, step)
            queue.append(state)

    while queue:
        state = queue.popleft()
        cx, cy, crot = state

        if not obstructed(board, piece, crot, cx - 1, cy):
            enqueue((cx - 1, cy, crot), state, MoveStep.Left)
        if not obstructed(board, piece, crot, cx + 1, cy):
            enqueue((cx + 1, cy, crot), state, MoveStep.Right)
        if not obstructed(board, piece, crot, cx, cy - 1):
            enqueue((cx, cy - 1, crot), state, MoveStep.SoftDrop)

        r = try_rotate(board, piece, crot, rot_cw(crot), cx, cy)
        if r is not None:
            enqueue(r, state, MoveStep.RotCW)
        r = try_rotate(board, piece, crot, rot_ccw(crot), cx, cy)
        if r is not None:
            enqueue(r, state, MoveStep.RotCCW)

    tgt_x, tgt_y, tgt_rot = target.x, target.y, target.rotation

    def landed_y(x: int, y: int, rot: Rotation) -> int:
        return y - board.drop_distance(piece, rot, x, y)

    best = None
    for state in parent:
        sx, sy, srot = state
        if srot == tgt_rot and sx == tgt_x and landed_y(sx, sy, srot) == tgt_y:
            if best is None or sy > best[1]:
                best = state

    if best is None:
        return None

    steps: list[MoveStep] = [MoveStep.HardDrop]
    cur = best
    while True:
        prev, step = parent[cur]
        if prev == cur:
            break
        steps.append(step)
        cur = prev

    steps.reverse()
    return steps


def apply_step(
    step: MoveStep, piece: Piece, rotation: Rotation, x: int, y: int, board: Board
) -> tuple[int, int, Rotation]:
    """Apply one move step, returning the new (x, y, rotation)."""
    match step:
        case MoveStep.Left:
            return (x - 1, y, rotation)
        case MoveStep.Right:
            return (x + 1, y, rotation)
        case MoveStep.SoftDrop:
            return (x, y - 1, rotation)
        case MoveStep.HardDrop:
            return (x, y - board.drop_distance(piece, rotation, x, y), rotation)
        case MoveStep.RotCW:
            r = try_rotate(board, piece, rotation, rot_cw(rotation), x, y)
            return r if r is not None else (x, y, rotation)
        case MoveStep.RotCCW:
            r = try_rotate(board, piece, rotation, rot_ccw(rotation), x, y)
            return r if r is not None else (x, y, rotation)
