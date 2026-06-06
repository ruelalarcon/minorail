from core.piece import Piece

RESET = "\033[0m"
DIM = "\033[2m"

PIECE_COLORS = {
    Piece.I: "\033[96m",  # cyan
    Piece.O: "\033[93m",  # yellow
    Piece.T: "\033[95m",  # magenta
    Piece.L: "\033[33m",  # orange
    Piece.J: "\033[94m",  # blue
    Piece.S: "\033[92m",  # green
    Piece.Z: "\033[91m",  # red
}


def colored(text: str, piece: Piece) -> str:
    return PIECE_COLORS[piece] + text + RESET
