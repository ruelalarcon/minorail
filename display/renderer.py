from __future__ import annotations

import sys
from typing import Optional

from core.board import piece_cells
from core.piece import Piece
from core.rotation import Rotation
from display.colors import DIM, RESET, colored
from game.state import GameState


def render(
    state: GameState,
    active_piece: Optional[Piece],
    active_loc: Optional[tuple[int, int, Rotation]],
    visible_rows: int,
    queue_size: int,
) -> None:
    grid: list[list[str]] = [["." for _ in range(10)] for _ in range(visible_rows)]

    for x in range(10):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                grid[y][x] = "#"

    if active_piece is not None and active_loc is not None:
        px, py, prot = active_loc
        drop = state.board.drop_distance(active_piece, prot, px, py)
        for gx, gy in piece_cells(active_piece, prot, px, py - drop):
            if 0 <= gx < 10 and 0 <= gy < visible_rows and grid[gy][gx] == ".":
                grid[gy][gx] = DIM + ":" + RESET
        for ax, ay in piece_cells(active_piece, prot, px, py):
            if 0 <= ax < 10 and 0 <= ay < visible_rows:
                grid[ay][ax] = colored(active_piece.value, active_piece)

    board_lines: list[str] = ["+" + "-" * 10 + "+"]
    for row in reversed(range(visible_rows)):
        board_lines.append("|" + "".join(grid[row]) + "|")
    board_lines.append("+" + "-" * 10 + "+")

    hold_str = colored(state.hold.value, state.hold) if state.hold else " "
    next_str = " ".join(colored(p.value, p) for p in state.queue[:queue_size])
    side: list[str] = [
        f"Hold: {hold_str}",
        f"Next: {next_str}",
        "",
        f"Combo:  {state.combo}",
        f"B2B:    {'Yes' if state.back_to_back else 'No'}",
    ]

    out: list[str] = []
    for i, row_str in enumerate(board_lines):
        out.append(f"{row_str}  {side[i] if i < len(side) else ''}")

    sys.stdout.write("\033[H")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()
