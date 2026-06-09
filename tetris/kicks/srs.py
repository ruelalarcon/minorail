from __future__ import annotations

from collections.abc import Sequence

from tetris.kicks.table import KickTable, TransitionKicks
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation

JLSTZ_PIECES = (Piece.J, Piece.L, Piece.S, Piece.T, Piece.Z)

JLSTZ_KICKS: TransitionKicks = {
    (Rotation.North, Rotation.East): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (Rotation.East, Rotation.North): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (Rotation.East, Rotation.South): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (Rotation.South, Rotation.East): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (Rotation.South, Rotation.West): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (Rotation.West, Rotation.South): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (Rotation.West, Rotation.North): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (Rotation.North, Rotation.West): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
}

I_KICKS: TransitionKicks = {
    (Rotation.North, Rotation.East): ((1, 0), (-1, 0), (2, 0), (-1, -1), (2, 2)),
    (Rotation.East, Rotation.North): ((-1, 0), (1, 0), (-2, 0), (1, 1), (-2, -2)),
    (Rotation.East, Rotation.South): ((0, -1), (-1, -1), (2, -1), (-1, 1), (2, -2)),
    (Rotation.South, Rotation.East): ((0, 1), (1, 1), (-2, 1), (1, -1), (-2, 2)),
    (Rotation.South, Rotation.West): ((-1, 1), (1, 1), (-2, 1), (1, 0), (-2, 0)),
    (Rotation.West, Rotation.South): ((1, -1), (-1, -1), (2, -1), (-1, 0), (2, 0)),
    (Rotation.West, Rotation.North): ((0, 1), (1, 1), (-2, 1), (1, -1), (-2, 2)),
    (Rotation.North, Rotation.West): ((0, -1), (-1, -1), (2, -1), (-1, 1), (2, -2)),
}


def _same_transitions(
    transitions: TransitionKicks, pieces: Sequence[Piece]
) -> dict[Piece, TransitionKicks]:
    return {piece: transitions for piece in pieces}


SRS = KickTable(
    kicks={
        Piece.I: I_KICKS,
        **_same_transitions(JLSTZ_KICKS, JLSTZ_PIECES),
    }
)
