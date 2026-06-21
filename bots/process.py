from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import Any, Callable, Optional

from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from sbp.codec import rules_message, to_jsonable
from sbp.messages import (
    MsgNewPiece,
    MsgPlay,
    MsgQuit,
    MsgStart,
    MsgStop,
    MsgSuggest,
)


class BotProcess:
    """Wraps an SBP bot subprocess with a background reader thread."""

    def __init__(
        self,
        exe_path: str,
        on_message: Callable[[dict[str, Any]], None],
        exe_args: Optional[list[str]] = None,
    ) -> None:
        self._proc = subprocess.Popen(
            [exe_path, *(exe_args or [])],
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
        self._send(to_jsonable(rules_message(rules)))

    def send_start(self, msg: MsgStart) -> None:
        self._send(to_jsonable(msg))

    def send_play(self, placement: Placement) -> None:
        self._send(to_jsonable(MsgPlay(placement)))

    def send_new_piece(self, piece: Piece) -> None:
        self._send(to_jsonable(MsgNewPiece(piece)))

    def send_suggest(
        self,
        incoming_garbage: list[int] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        self._send(to_jsonable(MsgSuggest(incoming_garbage, extensions)))

    def send_stop(self) -> None:
        self._send(to_jsonable(MsgStop()))

    def send_quit(self) -> None:
        self._send(to_jsonable(MsgQuit()))

    def wait(self, timeout: float = 5.0) -> None:
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.kill()

    def is_alive(self) -> bool:
        return self._proc.poll() is None
