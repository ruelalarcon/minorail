from __future__ import annotations

import json
import sys
import threading
import time
from typing import Any, Optional

from bot.process import BotProcess
from core.piece import Piece
from core.placement import Placement
from game.rules import Rules
from service.snapshot import BotSnapshot, PieceStreamSnapshot
from tbp.messages import BotCapabilities, MsgStart


class BotStartupError(RuntimeError):
    pass


class BotSession:
    def __init__(
        self, bot_path: str, info_print_topics: set[str] | None = None
    ) -> None:
        self._bot_path = bot_path
        self._info_print_topics = info_print_topics or set()
        self._bot: Optional[BotProcess] = None
        self._register_event = threading.Event()
        self._ready_event = threading.Event()
        self._suggestion_event = threading.Event()
        self._suggestion: Optional[list[Placement]] = None
        self._capabilities = BotCapabilities()

    def _on_bot_message(self, obj: dict[str, Any]) -> None:
        match obj.get("type"):
            case "register":
                self._capabilities = BotCapabilities.from_tbp(obj.get("capabilities"))
                print(
                    f"[info] {obj.get('name')} {obj.get('version')} by {obj.get('author')}",
                    file=sys.stderr,
                )
                self._register_event.set()
            case "info":
                self._handle_runtime_info(obj)
            case "ready":
                self._ready_event.set()
            case "suggestion":
                self._suggestion = [Placement.from_tbp(m) for m in obj.get("moves", [])]
                self._suggestion_event.set()
            case "error":
                print(f"[error] bot error: {obj.get('reason')}", file=sys.stderr)

    def start_from(self, snapshot: BotSnapshot, rules: Rules) -> None:
        self.close()
        self._register_event.clear()
        self._ready_event.clear()
        self._suggestion_event.clear()
        self._suggestion = None
        self._capabilities = BotCapabilities()
        self._bot = BotProcess(self._bot_path, self._on_bot_message)
        if not self._register_event.wait(timeout=5.0):
            self.close()
            raise BotStartupError("bot did not send register")

        capability_error = self._capabilities.validate_rules(rules)
        if capability_error is not None:
            self.close()
            raise BotStartupError(capability_error)

        self._bot.send_rules(rules)
        if not self._ready_event.wait(timeout=5.0):
            self.close()
            raise BotStartupError("bot did not send ready")
        self._bot.send_start(
            MsgStart(
                board=snapshot.board.copy(),
                queue=list(snapshot.queue),
                hold=snapshot.hold,
                combo=snapshot.combo,
                back_to_back=snapshot.back_to_back,
                piece_stream=self._start_piece_stream(snapshot.piece_stream),
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

    def _start_piece_stream(
        self, piece_stream: Optional[PieceStreamSnapshot]
    ) -> Optional[PieceStreamSnapshot]:
        if piece_stream is not None and not self._capabilities.piece_stream:
            print(
                "[warn] bot does not support piece_stream; omitting start.piece_stream",
                file=sys.stderr,
            )
            return None
        return piece_stream

    def _handle_runtime_info(self, obj: dict[str, Any]) -> None:
        topic = obj.get("topic")
        if not isinstance(topic, str) or topic not in self._info_print_topics:
            return
        data = obj.get("data")
        print(f"[bot info:{topic}] {json.dumps(data)}", file=sys.stderr)
