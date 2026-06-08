from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import Any, Callable, Optional

from core.piece import Piece
from core.placement import Placement
from game.rules import Rules
from tbp.messages import MsgStart


class BotProcess:
    """Wraps a TBP bot subprocess with a background reader thread."""

    def __init__(
        self, exe_path: str, on_message: Callable[[dict[str, Any]], None]
    ) -> None:
        self._proc = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
        )
        self._on_message = on_message
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"[error] invalid JSON from bot: {line}", file=sys.stderr)
                continue
            try:
                self._on_message(obj)
            except Exception as e:
                print(f"[error] bot message handler error: {e}", file=sys.stderr)

    def _send(self, obj: dict[str, Any]) -> None:
        line = (json.dumps(obj) + "\n").encode("utf-8")
        with self._lock:
            assert self._proc.stdin is not None
            self._proc.stdin.write(line)
            self._proc.stdin.flush()

    def send_rules(self, rules: Rules) -> None:
        self._send(
            {
                "type": "rules",
                "randomizer": rules.randomizer,
                "kickset": rules.kickset,
                "rot180": rules.rot180,
                "sonic_drop": rules.sonic_drop,
                "allspin_b2b": rules.allspin_b2b,
                "allclear_b2b": rules.allclear_b2b,
            }
        )

    def send_start(self, msg: MsgStart) -> None:
        board_rows: list[list[Optional[str]]] = [[None] * 10 for _ in range(40)]
        for x in range(10):
            for y in range(40):
                if msg.board.cols[x] & (1 << y):
                    board_rows[y][x] = "G"
        obj: dict[str, Any] = {
            "type": "start",
            "board": board_rows,
            "active": msg.active.to_tbp(),
            "queue": [p.value for p in msg.queue],
            "hold": msg.hold.value if msg.hold is not None else None,
            "combo": msg.combo,
            "back_to_back": msg.back_to_back,
        }
        if msg.piece_stream is not None:
            obj["piece_stream"] = {
                "offset": msg.piece_stream.offset,
                "pieces": [p.value for p in msg.piece_stream.pieces],
            }
        self._send(obj)

    def send_play(self, placement: Placement) -> None:
        self._send({"type": "play", "move": placement.to_tbp()})

    def send_new_piece(self, piece: Piece) -> None:
        self._send({"type": "new_piece", "piece": piece.value})

    def send_suggest(self) -> None:
        self._send({"type": "suggest"})

    def send_stop(self) -> None:
        self._send({"type": "stop"})

    def send_quit(self) -> None:
        self._send({"type": "quit"})

    def wait(self, timeout: float = 5.0) -> None:
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.kill()

    def is_alive(self) -> bool:
        return self._proc.poll() is None
