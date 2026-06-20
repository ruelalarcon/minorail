from __future__ import annotations

import atexit
import shutil
import sys

from tetris.model.piece import Piece

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
EMPTY = "  "
GHOST = DIM + ".." + RESET


def colored(text: str, piece: Piece) -> str:
    return PIECE_COLORS[piece] + text + RESET


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
