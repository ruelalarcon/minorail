from __future__ import annotations

from tetris.model.back_to_back_source import BackToBackSource
from tetris.model.piece import Piece
from tetris.model.rules import Rules
from tetris.model.spin import Spin


def clear_sources(
    piece: Piece,
    spin: Spin,
    lines_cleared: int,
    perfect_clear: bool,
) -> frozenset[BackToBackSource]:
    sources: set[BackToBackSource] = set()
    if lines_cleared == 4:
        sources.add(BackToBackSource.quad)
    if spin == Spin.full:
        sources.add(
            BackToBackSource.t_spin if piece == Piece.T else BackToBackSource.allspin
        )
    elif spin == Spin.mini:
        sources.add(
            BackToBackSource.t_spin_mini
            if piece == Piece.T
            else BackToBackSource.allspin_mini
        )
    if perfect_clear:
        sources.add(BackToBackSource.perfect_clear)
    return frozenset(sources)


def is_back_to_back_clear(
    piece: Piece,
    spin: Spin,
    lines_cleared: int,
    perfect_clear: bool,
    rules: Rules,
) -> bool:
    sources = clear_sources(piece, spin, lines_cleared, perfect_clear)
    return bool(sources & rules.back_to_back_sources)
