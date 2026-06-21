from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells


def obstructed(board: Board, piece: Piece, rotation: Rotation, x: int, y: int) -> bool:
    for cx, cy in piece_cells(piece, rotation, x, y):
        if cx < 0 or cx >= board.width or cy < 0:
            return True
        if cy < board.height and board.occupied(cx, cy):
            return True
    return False
