from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation, rot_ccw, rot_cw
from tetris.movegen.collision import obstructed
from tetris.movegen.rotation import try_rotate, try_rotate_180
from tetris.movegen.steps import MoveStep


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
