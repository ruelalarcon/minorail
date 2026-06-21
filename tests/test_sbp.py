from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

from bots.session import BotSession
from contracts.bot_snapshot import BotSnapshot
from bots.process import BotProcess
from sbp.state import game_state_from_start
from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rules import Rules
from tetris.game.state import spawn_location
from sbp.parser import parse
from sbp.messages import MsgRules, MsgStart, MsgSuggest


def empty_board() -> list[list[None]]:
    return [[None] * 10 for _ in range(40)]


class SbpParserTests(unittest.TestCase):
    def test_rules_accept_spawn_position(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "rules",
                    "spawn_x": 5,
                    "spawn_y": 18,
                }
            )
        )

        self.assertIsInstance(msg, MsgRules)
        assert isinstance(msg, MsgRules)
        self.assertEqual(msg.spawn_x, 5)
        self.assertEqual(msg.spawn_y, 18)

    def test_start_active_is_piece_string(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "start",
                    "board": empty_board(),
                    "active": "T",
                    "queue": ["I", "O"],
                    "hold": None,
                    "combo": 0,
                    "back_to_back": 0,
                }
            )
        )

        self.assertIsInstance(msg, MsgStart)
        assert isinstance(msg, MsgStart)
        self.assertEqual(msg.active, Piece.T)
        self.assertEqual(game_state_from_start(msg).active, spawn_location(Piece.T))

    def test_start_preserves_extensions_object(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "start",
                    "board": empty_board(),
                    "active": "T",
                    "queue": ["I", "O"],
                    "hold": None,
                    "combo": 0,
                    "back_to_back": 0,
                    "extensions": {"minorail.example.v1": {"value": True}},
                }
            )
        )

        self.assertIsInstance(msg, MsgStart)
        assert isinstance(msg, MsgStart)
        self.assertEqual(msg.extensions, {"minorail.example.v1": {"value": True}})

    def test_start_accepts_incoming_garbage(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "start",
                    "board": empty_board(),
                    "active": "T",
                    "queue": ["I", "O"],
                    "hold": None,
                    "combo": 0,
                    "back_to_back": 0,
                    "incoming_garbage": [4, 2],
                }
            )
        )

        self.assertIsInstance(msg, MsgStart)
        assert isinstance(msg, MsgStart)
        self.assertEqual(msg.incoming_garbage, [4, 2])

    def test_suggest_preserves_extensions_object(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "suggest",
                    "extensions": {"minorail.example.v1": {"value": True}},
                }
            )
        )

        self.assertIsInstance(msg, MsgSuggest)
        assert isinstance(msg, MsgSuggest)
        self.assertEqual(msg.extensions, {"minorail.example.v1": {"value": True}})

    def test_suggest_accepts_incoming_garbage(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "suggest",
                    "incoming_garbage": [4, 2],
                }
            )
        )

        self.assertIsInstance(msg, MsgSuggest)
        assert isinstance(msg, MsgSuggest)
        self.assertEqual(msg.incoming_garbage, [4, 2])

    def test_process_writes_extensions_on_start_and_suggest(self) -> None:
        sent: list[dict[str, Any]] = []

        def capture(obj: dict[str, Any]) -> None:
            sent.append(obj)

        process = BotProcess.__new__(BotProcess)
        process._send = capture

        incoming_garbage = [4, 2]
        extensions = {"minorail.example.v1": {"value": True}}
        process.send_start(
            MsgStart(
                board=Board(),
                active=Piece.T,
                queue=[Piece.I, Piece.O],
                hold=None,
                combo=0,
                back_to_back=0,
                incoming_garbage=incoming_garbage,
                extensions=extensions,
            )
        )
        process.send_suggest(incoming_garbage, extensions)

        self.assertEqual(sent[0]["incoming_garbage"], incoming_garbage)
        self.assertEqual(sent[0]["extensions"], extensions)
        self.assertEqual(
            sent[1],
            {
                "type": "suggest",
                "incoming_garbage": incoming_garbage,
                "extensions": extensions,
            },
        )

    def test_bot_session_reset_reuses_process_with_stop_start(self) -> None:
        class FakeProcess:
            instances: list["FakeProcess"] = []

            def __init__(
                self, exe_path: str, on_message: Any, exe_args: list[str] | None = None
            ) -> None:
                self.sent: list[str] = []
                self.alive = True
                self._on_message = on_message
                FakeProcess.instances.append(self)
                on_message(
                    {
                        "type": "register",
                        "capabilities": {
                            "randomizers": ["seven_bag"],
                            "kicksets": ["srs"],
                            "rot180": True,
                            "sonic_drop": ["only"],
                        },
                    }
                )

            def send_rules(self, rules: Rules) -> None:
                self.sent.append("rules")
                self._on_message({"type": "ready"})

            def send_start(self, msg: MsgStart) -> None:
                self.sent.append(f"start:{msg.active.value}")

            def send_stop(self) -> None:
                self.sent.append("stop")

            def send_quit(self) -> None:
                self.sent.append("quit")

            def wait(self, timeout: float = 5.0) -> None:
                self.sent.append("wait")
                self.alive = False

            def is_alive(self) -> bool:
                return self.alive

        first = BotSnapshot(Board(), Piece.T, [Piece.I], None, 0, 0)
        second = BotSnapshot(Board(), Piece.O, [Piece.L], None, 0, 0)

        with patch("bots.session.BotProcess", FakeProcess):
            session = BotSession("fake-bot")
            session.start_from(first, Rules())
            session.reset_from(second, Rules())

            self.assertEqual(len(FakeProcess.instances), 1)
            self.assertEqual(
                FakeProcess.instances[0].sent,
                ["rules", "start:T", "stop", "start:O"],
            )

            session.close()

        self.assertEqual(
            FakeProcess.instances[0].sent,
            ["rules", "start:T", "stop", "start:O", "quit", "wait"],
        )

    def test_start_rejects_active_location_object(self) -> None:
        msg = parse(
            json.dumps(
                {
                    "type": "start",
                    "board": empty_board(),
                    "active": {
                        "piece": "T",
                        "orientation": "north",
                        "x": 4,
                        "y": 19,
                    },
                    "queue": ["I", "O"],
                    "hold": None,
                    "combo": 0,
                    "back_to_back": 0,
                }
            )
        )

        self.assertIsNone(msg)


if __name__ == "__main__":
    unittest.main()
