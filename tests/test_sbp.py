from __future__ import annotations

import json
import unittest

from tetris.model.piece import Piece
from tetris.game.state import GameState, spawn_location
from protocols.sbp.parser import parse
from protocols.sbp.messages import MsgRules, MsgStart


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
        self.assertEqual(GameState.from_start(msg).active, spawn_location(Piece.T))

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
