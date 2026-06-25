from __future__ import annotations

import atexit
import shutil
import sys

from tetris.game.state import GameState
from tetris.model.board import cell_piece
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.pieces.cells import piece_cells

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

FILLED = "[]"
EMPTY = " ."
GHOST = "::"


def colored(text: str, piece: Piece) -> str:
    return PIECE_COLORS[piece] + text + RESET


def colored_cell(text: str, piece: Piece | None) -> str:
    if piece is None:
        return text
    return colored(text, piece)


def ghost_cell(piece: Piece) -> str:
    return DIM + PIECE_COLORS[piece] + GHOST + RESET


def board_width_columns(width: int) -> int:
    return 2 * width + 2


def render_board_lines(
    state: GameState,
    visible_rows: int,
    active: tuple[Piece, tuple[int, int, Rotation]] | None,
) -> list[str]:
    unset = "\x00"
    width = state.board.width
    visible_rows = min(visible_rows, state.board.height)
    grid: list[list[str]] = [[unset for _ in range(width)] for _ in range(visible_rows)]

    for x in range(width):
        for y in range(visible_rows):
            if state.board.occupied(x, y):
                grid[y][x] = colored_cell(FILLED, cell_piece(state.board.cell(x, y)))

    if active is not None:
        active_piece, active_loc = active
        px, py, prot = active_loc
        drop = state.board.drop_distance(active_piece, prot, px, py)
        for gx, gy in piece_cells(active_piece, prot, px, py - drop):
            if 0 <= gx < width and 0 <= gy < visible_rows and grid[gy][gx] == unset:
                grid[gy][gx] = ghost_cell(active_piece)
        for ax, ay in piece_cells(active_piece, prot, px, py):
            if 0 <= ax < width and 0 <= ay < visible_rows:
                grid[ay][ax] = colored(FILLED, active_piece)

    lines = ["+" + "--" * width + "+"]
    for row in reversed(range(visible_rows)):
        cells = "".join(EMPTY if cell == unset else cell for cell in grid[row])
        lines.append("|" + cells + "|")
    lines.append("+" + "--" * width + "+")
    return lines


def visible_len(value: str) -> int:
    return len(strip_ansi(value))


def pad_visible(value: str, width: int) -> str:
    return value + " " * max(0, width - visible_len(value))


def truncate_visible(value: str, width: int) -> str:
    if visible_len(value) <= width:
        return value

    result = ""
    visible = 0
    in_escape = False
    saw_escape = False
    for char in value:
        if visible >= width:
            break
        result += char
        if char == "\033":
            in_escape = True
            saw_escape = True
        elif in_escape and char == "m":
            in_escape = False
        elif not in_escape:
            visible += 1
    if saw_escape and not result.endswith(RESET):
        result += RESET
    return result


def strip_ansi(value: str) -> str:
    result = ""
    in_escape = False
    for char in value:
        if char == "\033":
            in_escape = True
        elif in_escape and char == "m":
            in_escape = False
        elif not in_escape:
            result += char
    return result


class LiveTerminalRegion:
    def __init__(self) -> None:
        self._interactive = sys.stdout.isatty()
        self._frame_height = 0
        self._configured_key: tuple[int, int] | None = None
        self._last_drawn_height = 0
        self._registered_reset = False

    def start(self, frame_height: int) -> None:
        self._frame_height = max(1, frame_height)
        self._last_drawn_height = 0
        if not self._interactive:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            return

        self._configure(force=True)

    def render(self, lines: list[str]) -> None:
        if not self._interactive:
            sys.stdout.write("\033[H")
            sys.stdout.write("\n".join(f"{line}\033[K" for line in lines) + "\n")
            sys.stdout.flush()
            return

        self._frame_height = max(self._frame_height, len(lines))
        self._configure()
        draw_height = max(len(lines), self._last_drawn_height)
        frame_lines = lines + [""] * (draw_height - len(lines))

        sys.stdout.write("\0337")
        sys.stdout.write("\033[H")
        sys.stdout.write("\n".join(f"{line}\033[K" for line in frame_lines))
        sys.stdout.write("\0338")
        sys.stdout.flush()
        self._last_drawn_height = draw_height

    def reset(self) -> None:
        if not self._interactive:
            return
        sys.stdout.write("\033[r\033[0m")
        sys.stdout.flush()

    def _configure(self, *, force: bool = False) -> None:
        _, rows = shutil.get_terminal_size(fallback=(80, 24))
        visual_rows = min(self._frame_height, max(1, rows - 1))
        log_top = min(visual_rows + 1, rows)
        key = (log_top, rows)
        if not self._registered_reset:
            atexit.register(self.reset)
            self._registered_reset = True
        if force or key != self._configured_key:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(f"\033[{log_top};{rows}r")
            sys.stdout.write(f"\033[{log_top};1H")
            sys.stdout.flush()
            self._configured_key = key
            self._last_drawn_height = 0
