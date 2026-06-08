from __future__ import annotations

import sys
import threading
import time
from typing import Any, Optional

from bot.process import BotProcess
from core.piece import Piece
from core.placement import Placement
from game.rules import Rules
from service.snapshot import BotSnapshot
from tbp.messages import MsgStart


class BotSession:
    def __init__(self, bot_path: str) -> None:
        self._bot_path = bot_path
        self._bot: Optional[BotProcess] = None
        self._ready_event = threading.Event()
        self._suggestion_event = threading.Event()
        self._suggestion: Optional[list[Placement]] = None

    def _on_bot_message(self, obj: dict[str, Any]) -> None:
        match obj.get("type"):
            case "info":
                print(
                    f"[info] {obj.get('name')} {obj.get('version')} by {obj.get('author')}",
                    file=sys.stderr,
                )
            case "ready":
                self._ready_event.set()
            case "suggestion":
                self._suggestion = [Placement.from_tbp(m) for m in obj.get("moves", [])]
                self._suggestion_event.set()
            case "error":
                print(f"[bot error] {obj.get('reason')}", file=sys.stderr)

    def start_from(self, snapshot: BotSnapshot, rules: Rules) -> None:
        self.close()
        self._ready_event.clear()
        self._suggestion_event.clear()
        self._suggestion = None
        self._bot = BotProcess(self._bot_path, self._on_bot_message)
        time.sleep(0.1)
        self._bot.send_rules(rules)
        if not self._ready_event.wait(timeout=5.0):
            self.close()
            raise TimeoutError("bot did not send ready")
        self._bot.send_start(
            MsgStart(
                board=snapshot.board.copy(),
                queue=list(snapshot.queue),
                hold=snapshot.hold,
                combo=snapshot.combo,
                back_to_back=snapshot.back_to_back,
                piece_stream=snapshot.piece_stream,
            )
        )

    def suggest(self, timeout_ms: int) -> list[Placement]:
        if self._bot is None:
            raise RuntimeError("bot session has not been started")
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            self._suggestion_event.clear()
            self._suggestion = None
            self._bot.send_suggest()
            wait_time = min(5.0, max(0.0, deadline - time.time()))
            if not self._suggestion_event.wait(timeout=wait_time):
                return []
            moves = self._suggestion or []
            if moves:
                return moves
            time.sleep(0.05)
        return []

    def advance_with(
        self, placement: Placement, new_pieces: list[Piece] | None = None
    ) -> None:
        if self._bot is None:
            return
        self._bot.send_play(placement)
        for piece in new_pieces or []:
            self._bot.send_new_piece(piece)

    def reset_from(self, snapshot: BotSnapshot, rules: Rules) -> None:
        self.start_from(snapshot, rules)

    def stop(self) -> None:
        if self._bot is not None and self._bot.is_alive():
            self._bot.send_stop()

    def close(self) -> None:
        if self._bot is None:
            return
        if self._bot.is_alive():
            try:
                self._bot.send_quit()
            except Exception:
                pass
        self._bot.wait(timeout=3.0)
        self._bot = None
