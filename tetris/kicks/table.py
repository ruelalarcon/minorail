from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from tetris.model.piece import Piece
from tetris.model.rotation import Rotation

KickList = tuple[tuple[int, int], ...]
Transition = tuple[Rotation, Rotation]
TransitionKicks = Mapping[Transition, KickList]
PieceKicks = Mapping[Piece, TransitionKicks]

NO_KICKS: KickList = ()


@dataclass(frozen=True)
class KickTable:
    kicks: PieceKicks

    def kicks_between(
        self, piece: Piece, from_rot: Rotation, to_rot: Rotation
    ) -> KickList:
        return self.kicks.get(piece, {}).get((from_rot, to_rot), NO_KICKS)
