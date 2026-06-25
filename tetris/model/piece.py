from enum import Enum


class Piece(Enum):
    I = "I"  # noqa: E741
    J = "J"
    L = "L"
    O = "O"  # noqa: E741
    S = "S"
    T = "T"
    Z = "Z"


PIECE_ORDER = "IJLOSTZ"
PIECES = tuple(Piece(letter) for letter in PIECE_ORDER)
