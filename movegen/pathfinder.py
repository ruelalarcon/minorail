from __future__ import annotations

from collections import deque
from enum import Enum
from typing import TYPE_CHECKING, Optional

from core.board import Board, piece_cells
from core.location import PieceLocation
from core.piece import Piece
from core.rotation import Rotation, rot_ccw, rot_cw
from movegen import kicks

if TYPE_CHECKING:
    from game.rules import Rules


class MoveStep(Enum):
    Left = "left"
    Right = "right"
    DasLeft = "das_left"
    DasRight = "das_right"
    RotCW = "rot_cw"
    RotCCW = "rot_ccw"
    Rot180 = "rot_180"
    SoftDrop = "soft_drop"
    SonicDrop = "sonic_drop"
    HardDrop = "hard_drop"


def obstructed(board: Board, piece: Piece, rotation: Rotation, x: int, y: int) -> bool:
    for cx, cy in piece_cells(piece, rotation, x, y):
        if cx < 0 or cx >= 10 or cy < 0:
            return True
        if cy < 40 and board.occupied(cx, cy):
            return True
    return False


def try_rotate(
    board: Board,
    piece: Piece,
    from_rot: Rotation,
    to_rot: Rotation,
    x: int,
    y: int,
    kickset: str,
) -> Optional[tuple[int, int, Rotation]]:
    if piece == Piece.O:
        return None
    kick_list = (
        kicks.kicks_cw(kickset, piece, from_rot)
        if to_rot == rot_cw(from_rot)
        else kicks.kicks_ccw(kickset, piece, from_rot)
    )
    for dx, dy in kick_list:
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
    for dx, dy in kicks.kicks_180(kickset, piece, from_rot):
        nx, ny = x + dx, y + dy
        if not obstructed(board, piece, to_rot, nx, ny):
            return (nx, ny, to_rot)
    return None


def find_path(
    board: Board,
    piece: Piece,
    target: PieceLocation,
    rules: Rules,
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

    use_rot180 = rules.rot180
    tgt_x, tgt_y, tgt_rot = target.x, target.y, target.rotation

    best: Optional[tuple[int, int, Rotation]] = None
    while queue:
        state = queue.popleft()
        cx, cy, crot = state
        if (
            crot == tgt_rot
            and cx == tgt_x
            and cy - board.drop_distance(piece, crot, cx, cy) == tgt_y
        ):
            best = state
            break

        # Lateral moves
        if not obstructed(board, piece, crot, cx - 1, cy):
            enqueue((cx - 1, cy, crot), state, MoveStep.Left)
        if not obstructed(board, piece, crot, cx + 1, cy):
            enqueue((cx + 1, cy, crot), state, MoveStep.Right)

        # DAS: slide all the way left/right
        das_x = cx - 1
        while not obstructed(board, piece, crot, das_x, cy):
            das_x -= 1
        das_x += 1
        if das_x != cx:
            enqueue((das_x, cy, crot), state, MoveStep.DasLeft)

        das_x = cx + 1
        while not obstructed(board, piece, crot, das_x, cy):
            das_x += 1
        das_x -= 1
        if das_x != cx:
            enqueue((das_x, cy, crot), state, MoveStep.DasRight)

        # Vertical moves
        if rules.sonic_drop != "only":
            if not obstructed(board, piece, crot, cx, cy - 1):
                enqueue((cx, cy - 1, crot), state, MoveStep.SoftDrop)

        sonic_y = cy - board.drop_distance(piece, crot, cx, cy)
        if sonic_y != cy:
            enqueue((cx, sonic_y, crot), state, MoveStep.SonicDrop)

        # Rotations
        r = try_rotate(board, piece, crot, rot_cw(crot), cx, cy, rules.kickset)
        if r is not None:
            enqueue(r, state, MoveStep.RotCW)
        r = try_rotate(board, piece, crot, rot_ccw(crot), cx, cy, rules.kickset)
        if r is not None:
            enqueue(r, state, MoveStep.RotCCW)
        if use_rot180:
            r = try_rotate_180(board, piece, crot, cx, cy, rules.kickset)
            if r is not None:
                enqueue(r, state, MoveStep.Rot180)

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


def convert_sonic_drops(
    path: list[MoveStep],
    board: Board,
    piece: Piece,
    kickset: str = "srs",
) -> list[MoveStep]:
    spawn_x, spawn_y, spawn_rot = 4, 19, Rotation.North
    if obstructed(board, piece, spawn_rot, spawn_x, spawn_y):
        spawn_y = 20

    x, y, rotation = spawn_x, spawn_y, spawn_rot
    converted: list[MoveStep] = []
    for step in path:
        if step == MoveStep.SonicDrop:
            distance = board.drop_distance(piece, rotation, x, y)
            converted.extend(MoveStep.SoftDrop for _ in range(distance))
            y -= distance
            continue

        converted.append(step)
        x, y, rotation = apply_step(step, piece, rotation, x, y, board, kickset)

    return converted


def apply_step(
    step: MoveStep,
    piece: Piece,
    rotation: Rotation,
    x: int,
    y: int,
    board: Board,
    kickset: str = "srs",
) -> tuple[int, int, Rotation]:
    match step:
        case MoveStep.Left:
            return (x - 1, y, rotation)
        case MoveStep.Right:
            return (x + 1, y, rotation)
        case MoveStep.DasLeft:
            nx = x - 1
            while not obstructed(board, piece, rotation, nx, y):
                nx -= 1
            return (nx + 1, y, rotation)
        case MoveStep.DasRight:
            nx = x + 1
            while not obstructed(board, piece, rotation, nx, y):
                nx += 1
            return (nx - 1, y, rotation)
        case MoveStep.SoftDrop:
            return (x, y - 1, rotation)
        case MoveStep.SonicDrop:
            return (x, y - board.drop_distance(piece, rotation, x, y), rotation)
        case MoveStep.HardDrop:
            return (x, y - board.drop_distance(piece, rotation, x, y), rotation)
        case MoveStep.RotCW:
            r = try_rotate(board, piece, rotation, rot_cw(rotation), x, y, kickset)
            return r if r is not None else (x, y, rotation)
        case MoveStep.RotCCW:
            r = try_rotate(board, piece, rotation, rot_ccw(rotation), x, y, kickset)
            return r if r is not None else (x, y, rotation)
        case MoveStep.Rot180:
            r = try_rotate_180(board, piece, rotation, x, y, kickset)
            return r if r is not None else (x, y, rotation)
