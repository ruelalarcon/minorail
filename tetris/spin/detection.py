from __future__ import annotations

from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.model.spin_detection import SpinDetection
from tetris.model.board import Board
from tetris.spin.immobility import immobile
from tetris.spin.t_spin import detect_t_spin


def detect_spin(
    location: PieceLocation,
    board: Board,
    *,
    rules: Rules,
    rotated: bool,
    kick_index: int | None = None,
) -> Spin:
    mode = rules.spin_detection
    if mode == SpinDetection.none or not rotated:
        return Spin.none

    if location.piece == Piece.T:
        t_spin = detect_t_spin(
            location,
            board,
            rotated=rotated,
            kick_index=kick_index,
            force_mini=mode == SpinDetection.mini_only,
        )
        if t_spin != Spin.none:
            return t_spin
        if mode in {
            SpinDetection.t_spins_plus,
            SpinDetection.all_plus,
            SpinDetection.all_mini_plus,
            SpinDetection.mini_only,
        } and immobile(location, board):
            return Spin.mini
        return Spin.none

    if mode in {SpinDetection.all, SpinDetection.all_plus} and immobile(
        location, board
    ):
        return Spin.full
    if mode in {
        SpinDetection.all_mini,
        SpinDetection.all_mini_plus,
        SpinDetection.mini_only,
    } and immobile(location, board):
        return Spin.mini
    return Spin.none
