from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation

SPAWN_X = 4
SPAWN_Y = 19


def spawn_location(piece: Piece) -> PieceLocation:
    return PieceLocation(piece, Rotation.North, SPAWN_X, SPAWN_Y)
