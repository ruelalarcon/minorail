from __future__ import annotations

import unittest

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.movegen.steps import MoveStep
from suggestion.contracts.suggestion_result import SuggestionResult
from suggestion.contracts.suggestion_status import SuggestionStatus
from suggestion.websocket_api import (
    WebSocketApiError,
    request_from_json,
    result_to_json,
)


class WebSocketApiTests(unittest.TestCase):
    def test_request_active_is_piece_string(self) -> None:
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": {"cols": [0] * 10},
                "active": "T",
                "queue": ["I", "O"],
                "hold": None,
                "can_hold": True,
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.snapshot.seq, 7)
        self.assertEqual(request.snapshot.active.piece, Piece.T)
        self.assertEqual(request.snapshot.active.rotation, Rotation.North)
        self.assertEqual(request.snapshot.active.x, 4)
        self.assertEqual(request.snapshot.active.y, 19)
        self.assertEqual(request.snapshot.queue, [Piece.I, Piece.O])
        self.assertEqual(request.snapshot.board, Board([0] * 10))

    def test_request_rules_can_override_spawn_position(self) -> None:
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": {"cols": [0] * 10},
                "active": "T",
                "queue": ["I", "O"],
                "rules": {"spawn_x": 5, "spawn_y": 18},
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.rules.spawn_x, 5)
        self.assertEqual(request.rules.spawn_y, 18)
        self.assertEqual(request.snapshot.active.x, 5)
        self.assertEqual(request.snapshot.active.y, 18)

    def test_request_rejects_active_location_object(self) -> None:
        with self.assertRaises(WebSocketApiError) as cm:
            request_from_json(
                {
                    "type": "suggest",
                    "seq": 7,
                    "board": {"cols": [0] * 10},
                    "active": {
                        "type": "T",
                        "orientation": "north",
                        "x": 4,
                        "y": 19,
                    },
                    "queue": ["I", "O"],
                    "hold": None,
                    "can_hold": True,
                },
                base_rules=Rules(),
            )

        self.assertEqual(cm.exception.reason, "invalid_request")
        self.assertEqual(cm.exception.message, "active must be a piece string")

    def test_result_json_uses_python_contract_field_names(self) -> None:
        placement = Placement(
            PieceLocation(Piece.T, Rotation.South, 4, 1),
            Spin.full,
        )
        response = result_to_json(
            SuggestionResult(
                seq=7,
                status=SuggestionStatus.Synced,
                placements=[placement],
                placement=placement,
                path=[MoveStep.Rot180, MoveStep.HardDrop],
            )
        )

        self.assertEqual(response["type"], "suggestion")
        self.assertEqual(response["seq"], 7)
        self.assertEqual(response["status"], "synced")
        self.assertEqual(response["placement"], placement.to_sbp())
        self.assertEqual(response["placements"], [placement.to_sbp()])
        self.assertEqual(response["path"], ["rot_180", "hard_drop"])
        self.assertIsNone(response["reason"])


if __name__ == "__main__":
    unittest.main()
