from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation

SPAWN_X = 4
SPAWN_Y = 19


def spawn_location(piece: Piece, x: int = SPAWN_X, y: int = SPAWN_Y) -> PieceLocation:
    return PieceLocation(piece, Rotation.North, x, y)
