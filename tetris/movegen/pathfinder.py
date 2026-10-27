from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Optional

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation, rot_ccw, rot_cw
from tetris.model.spin import Spin
from tetris.kicks.registry import kick_table
from tetris.spin.detection import detect_spin
from tetris.movegen.collision import obstructed
from tetris.movegen.rotation import try_rotate, try_rotate_180
from tetris.movegen.stepper import apply_step
from tetris.movegen.steps import MoveStep

if TYPE_CHECKING:
    from tetris.model.rules import Rules


def find_path(
    board: Board,
    piece: Piece,
    target: PieceLocation,
    rules: Rules,
    *,
    required_spin: Spin | None = None,
) -> Optional[list[MoveStep]]:
    """
    BFS from the configured spawn to the target placement.
    Returns a path ending with HardDrop, or None if unreachable.
    An optional spin constraint tracks flags earned by rotations. Translation
    clears them; hard drop preserves them, matching the TETR.IO input model.
    """
    spawn_x, spawn_y, spawn_rot = rules.spawn_x, rules.spawn_y, Rotation.North
    if obstructed(board, piece, spawn_rot, spawn_x, spawn_y):
        spawn_y += 1
        if obstructed(board, piece, spawn_rot, spawn_x, spawn_y):
            return None

    start = (spawn_x, spawn_y, spawn_rot, Spin.none)
    parent: dict[
        tuple[int, int, Rotation, Spin],
        tuple[tuple[int, int, Rotation, Spin], MoveStep],
    ] = {start: (start, MoveStep.HardDrop)}
    queue: deque[tuple[int, int, Rotation, Spin]] = deque([start])

    def enqueue(
        state: tuple[int, int, Rotation, Spin],
        prev: tuple[int, int, Rotation, Spin],
        step: MoveStep,
    ) -> None:
        if state not in parent:
            parent[state] = (prev, step)
            queue.append(state)

    use_rot180 = rules.rot180
    tgt_x, tgt_y, tgt_rot = target.x, target.y, target.rotation

    def rotation_spin(
        cx: int, cy: int, crot: Rotation, rotated: tuple[int, int, Rotation]
    ) -> Spin:
        if required_spin is None:
            return Spin.none
        nx, ny, nrot = rotated
        kicks = kick_table(rules.kickset).kicks_between(piece, crot, nrot)
        index = kicks.index((nx - cx, ny - cy))
        return detect_spin(
            PieceLocation(piece, nrot, nx, ny),
            board,
            rules=rules,
            rotated=True,
            kick_index=index,
        )

    best: Optional[tuple[int, int, Rotation, Spin]] = None
    while queue:
        state = queue.popleft()
        cx, cy, crot, spin = state
        if (
            crot == tgt_rot
            and cx == tgt_x
            and cy - board.drop_distance(piece, crot, cx, cy) == tgt_y
            and (required_spin is None or spin == required_spin)
        ):
            best = state
            break

        if not obstructed(board, piece, crot, cx - 1, cy):
            enqueue((cx - 1, cy, crot, Spin.none), state, MoveStep.Left)
        if not obstructed(board, piece, crot, cx + 1, cy):
            enqueue((cx + 1, cy, crot, Spin.none), state, MoveStep.Right)

        das_x = cx - 1
        while not obstructed(board, piece, crot, das_x, cy):
            das_x -= 1
        das_x += 1
        if das_x != cx:
            enqueue((das_x, cy, crot, Spin.none), state, MoveStep.DasLeft)

        das_x = cx + 1
        while not obstructed(board, piece, crot, das_x, cy):
            das_x += 1
        das_x -= 1
        if das_x != cx:
            enqueue((das_x, cy, crot, Spin.none), state, MoveStep.DasRight)

        r = try_rotate(board, piece, crot, rot_cw(crot), cx, cy, rules.kickset)
        if r is not None:
            enqueue((*r, rotation_spin(cx, cy, crot, r)), state, MoveStep.RotCW)
        r = try_rotate(board, piece, crot, rot_ccw(crot), cx, cy, rules.kickset)
        if r is not None:
            enqueue((*r, rotation_spin(cx, cy, crot, r)), state, MoveStep.RotCCW)
        if use_rot180:
            r = try_rotate_180(board, piece, crot, cx, cy, rules.kickset)
            if r is not None:
                enqueue((*r, rotation_spin(cx, cy, crot, r)), state, MoveStep.Rot180)

        if rules.sonic_drop != "only" and not obstructed(
            board, piece, crot, cx, cy - 1
        ):
            enqueue((cx, cy - 1, crot, Spin.none), state, MoveStep.SoftDrop)

        sonic_y = cy - board.drop_distance(piece, crot, cx, cy)
        if sonic_y != cy:
            enqueue((cx, sonic_y, crot, Spin.none), state, MoveStep.SonicDrop)

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
    spawn_x: int = 4,
    spawn_y: int = 20,
) -> list[MoveStep]:
    spawn_rot = Rotation.North
    if obstructed(board, piece, spawn_rot, spawn_x, spawn_y):
        spawn_y += 1

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


__all__ = [
    "MoveStep",
    "apply_step",
    "convert_sonic_drops",
    "find_path",
    "obstructed",
    "try_rotate",
    "try_rotate_180",
]
