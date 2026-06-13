from __future__ import annotations

from tetris.kicks.srs import JLSTZ_KICKS, ZERO_180_KICKS
from tetris.kicks.table import KickTable, TransitionKicks
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation

JLSTZ_180_KICKS: TransitionKicks = {
    (Rotation.North, Rotation.South): (
        (0, 0),
        (0, 1),
        (1, 1),
        (-1, 1),
        (1, 0),
        (-1, 0),
    ),
    (Rotation.East, Rotation.West): (
        (0, 0),
        (1, 0),
        (1, 2),
        (1, 1),
        (0, 2),
        (0, 1),
    ),
    (Rotation.South, Rotation.North): (
        (0, 0),
        (0, -1),
        (-1, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
    ),
    (Rotation.West, Rotation.East): (
        (0, 0),
        (-1, 0),
        (-1, 2),
        (-1, 1),
        (0, 2),
        (0, 1),
    ),
}

I_KICKS: TransitionKicks = {
    (Rotation.North, Rotation.East): ((1, 0), (2, 0), (-1, 0), (-1, -1), (2, 2)),
    (Rotation.East, Rotation.North): ((-1, 0), (-2, 0), (1, 0), (-2, -2), (1, 1)),
    (Rotation.East, Rotation.South): ((0, -1), (-1, -1), (2, -1), (-1, 1), (2, -2)),
    (Rotation.South, Rotation.East): ((0, 1), (-2, 1), (1, 1), (-2, 2), (1, -1)),
    (Rotation.South, Rotation.West): ((-1, 0), (1, 0), (-2, 0), (1, 1), (-2, -2)),
    (Rotation.West, Rotation.South): ((1, 0), (2, 0), (-1, 0), (2, 2), (-1, -1)),
    (Rotation.West, Rotation.North): ((0, 1), (1, 1), (-2, 1), (1, -1), (-2, 2)),
    (Rotation.North, Rotation.West): ((0, -1), (-1, -1), (2, -1), (2, -2), (-1, 1)),
    (Rotation.North, Rotation.South): ((1, -1), (1, 0)),
    (Rotation.East, Rotation.West): ((-1, -1), (0, -1)),
    (Rotation.South, Rotation.North): ((-1, 1), (-1, 0)),
    (Rotation.West, Rotation.East): ((1, 1), (0, 1)),
}

SRS_PLUS = KickTable(
    kicks={
        Piece.I: I_KICKS,
        Piece.O: ZERO_180_KICKS,
        Piece.J: {**JLSTZ_KICKS, **JLSTZ_180_KICKS},
        Piece.L: {**JLSTZ_KICKS, **JLSTZ_180_KICKS},
        Piece.S: {**JLSTZ_KICKS, **JLSTZ_180_KICKS},
        Piece.T: {**JLSTZ_KICKS, **JLSTZ_180_KICKS},
        Piece.Z: {**JLSTZ_KICKS, **JLSTZ_180_KICKS},
    }
)
