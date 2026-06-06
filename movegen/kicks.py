from core.piece import Piece
from core.rotation import Rotation


def srs_offsets(piece: Piece, rotation: Rotation) -> list[tuple[int, int]]:
    """SRS true-rotation offset table."""
    if piece == Piece.O:
        match rotation:
            case Rotation.North:
                return [(0, 0)] * 5
            case Rotation.East:
                return [(0, -1)] * 5
            case Rotation.South:
                return [(-1, -1)] * 5
            case Rotation.West:
                return [(-1, 0)] * 5
    if piece == Piece.I:
        match rotation:
            case Rotation.North:
                return [(0, 0), (-1, 0), (2, 0), (-1, 0), (2, 0)]
            case Rotation.East:
                return [(-1, 0), (0, 0), (0, 0), (0, 1), (0, -2)]
            case Rotation.South:
                return [(-1, 1), (1, 1), (-2, 1), (1, 0), (-2, 0)]
            case Rotation.West:
                return [(0, 1), (0, 1), (0, 1), (0, -1), (0, 2)]
    # J, L, S, T, Z
    match rotation:
        case Rotation.North:
            return [(0, 0)] * 5
        case Rotation.East:
            return [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)]
        case Rotation.South:
            return [(0, 0)] * 5
        case Rotation.West:
            return [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)]


def srs_kicks(
    piece: Piece, from_rot: Rotation, to_rot: Rotation
) -> list[tuple[int, int]]:
    """Kick offsets when rotating from_rot -> to_rot."""
    frm = srs_offsets(piece, from_rot)
    to = srs_offsets(piece, to_rot)
    return [(frm[i][0] - to[i][0], frm[i][1] - to[i][1]) for i in range(5)]
