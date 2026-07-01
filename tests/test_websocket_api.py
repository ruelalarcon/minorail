from __future__ import annotations

import asyncio
import unittest

from tetris.model.board import GARBAGE_CELL, PIECE_TO_CELL, Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.rules import Rules
from tetris.model.spin import Spin
from tetris.movegen.steps import MoveStep
from api.websocket import (
    SuggestionWebSocketServer,
    WebSocketApiError,
    advance_request_from_json,
    advance_result_to_json,
    close_session_request_from_json,
    close_session_result_to_json,
    request_from_json,
    result_to_json,
)
from contracts.suggestion_result import SuggestionResult
from contracts.suggestion_status import SuggestionStatus


def _empty_board(width: int = 10, height: int = 40) -> list[list[None]]:
    return [[None] * width for _ in range(height)]


class WebSocketApiTests(unittest.IsolatedAsyncioTestCase):
    def test_request_active_is_piece_string(self) -> None:
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": _empty_board(),
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
        self.assertEqual(request.snapshot.active.y, 20)
        self.assertEqual(request.snapshot.queue, [Piece.I, Piece.O])
        self.assertEqual(request.snapshot.board, Board.empty())

    def test_request_rules_can_override_spawn_position(self) -> None:
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": _empty_board(),
                "active": "T",
                "queue": ["I", "O"],
                "rules": {"spawn_position": {"x": 5, "y": 18}},
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.rules.spawn_x, 5)
        self.assertEqual(request.rules.spawn_y, 18)
        self.assertEqual(request.snapshot.active.x, 5)
        self.assertEqual(request.snapshot.active.y, 18)

    def test_request_rules_define_board_size_for_sbp_matrix(self) -> None:
        rows: list[list[str | None]] = [[None, None] for _ in range(100)]
        rows[70][1] = "G"

        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": rows,
                "active": "T",
                "queue": ["I", "O"],
                "rules": {"board_size": {"width": 2, "height": 100}},
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.snapshot.board, Board([0, 1 << 70], height=100))

    def test_request_sbp_matrix_accepts_any_non_null_cell(self) -> None:
        rows: list[list[object | None]] = [[None, None] for _ in range(4)]
        rows[0][0] = "T"
        rows[1][1] = 123
        rows[2][0] = True

        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": rows,
                "active": "T",
                "queue": ["I", "O"],
                "rules": {"board_size": {"width": 2, "height": 4}},
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.snapshot.board.cell(0, 0), PIECE_TO_CELL[Piece.T])
        self.assertEqual(request.snapshot.board.cell(1, 1), GARBAGE_CELL)
        self.assertEqual(request.snapshot.board.cell(0, 2), GARBAGE_CELL)

    def test_request_accepts_extensions_object(self) -> None:
        extensions = {"minorail.example.v1": {"value": True}}
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": _empty_board(),
                "active": "T",
                "queue": ["I", "O"],
                "extensions": extensions,
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.extensions, extensions)
        self.assertIsNot(request.extensions, extensions)

    def test_request_accepts_incoming_garbage(self) -> None:
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": _empty_board(),
                "active": "T",
                "queue": ["I", "O"],
                "incoming_garbage": [4, 2],
            },
            base_rules=Rules(),
        )

        self.assertEqual(request.incoming_garbage, [4, 2])

    def test_request_uses_pathfinding_field(self) -> None:
        request = request_from_json(
            {
                "type": "suggest",
                "seq": 7,
                "board": _empty_board(),
                "active": "T",
                "queue": ["I", "O"],
                "pathfinding": False,
            },
            base_rules=Rules(),
            default_pathfinding=True,
        )

        self.assertFalse(request.pathfinding)

    def test_request_rejects_non_object_extensions(self) -> None:
        with self.assertRaises(WebSocketApiError) as cm:
            request_from_json(
                {
                    "type": "suggest",
                    "seq": 7,
                    "board": _empty_board(),
                    "active": "T",
                    "queue": ["I", "O"],
                    "extensions": ["minorail.example.v1"],
                },
                base_rules=Rules(),
            )

        self.assertEqual(cm.exception.reason, "invalid_request")
        self.assertEqual(cm.exception.message, "extensions must be an object")

    def test_request_rejects_active_location_object(self) -> None:
        with self.assertRaises(WebSocketApiError) as cm:
            request_from_json(
                {
                    "type": "suggest",
                    "seq": 7,
                    "board": _empty_board(),
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

    def test_advance_request_accepts_placement_and_session(self) -> None:
        placement = Placement(PieceLocation(Piece.T, Rotation.South, 4, 1), Spin.full)

        request = advance_request_from_json(
            {
                "type": "advance",
                "seq": 8,
                "session_id": "game-1",
                "placement": placement.to_sbp(),
                "rules": {"spawn_position": {"x": 4, "y": 21}},
            },
            base_rules=Rules(),
        )

        self.assertEqual(request["session_id"], "game-1")
        self.assertEqual(request["placement"], placement)
        self.assertEqual(request["rules"].spawn_y, 21)

    def test_advance_request_rejects_missing_placement(self) -> None:
        with self.assertRaises(WebSocketApiError) as cm:
            advance_request_from_json(
                {"type": "advance", "seq": 8},
                base_rules=Rules(),
            )

        self.assertEqual(cm.exception.reason, "invalid_request")
        self.assertEqual(cm.exception.message, "placement must be an object")

    def test_advance_result_json(self) -> None:
        self.assertEqual(
            advance_result_to_json(8, True),
            {"type": "advance", "seq": 8, "accepted": True},
        )

    def test_close_session_request_accepts_session(self) -> None:
        request = close_session_request_from_json(
            {
                "type": "close_session",
                "seq": 9,
                "session_id": "game-1",
            },
        )

        self.assertEqual(request["session_id"], "game-1")

    def test_close_session_request_uses_default_session(self) -> None:
        request = close_session_request_from_json(
            {
                "type": "close_session",
                "seq": 9,
            },
            default_session_id="connection-1",
        )

        self.assertEqual(request["session_id"], "connection-1")

    def test_close_session_result_json(self) -> None:
        self.assertEqual(
            close_session_result_to_json(9, True),
            {"type": "close_session", "seq": 9, "closed": True},
        )

    async def test_close_session_message_closes_service_session(self) -> None:
        class FakeService:
            def __init__(self) -> None:
                self.closed_session_ids: list[str] = []

            def close_session(self, session_id: str) -> bool:
                self.closed_session_ids.append(session_id)
                return True

        server = SuggestionWebSocketServer.__new__(SuggestionWebSocketServer)
        server._service = FakeService()
        server._lock = asyncio.Lock()
        session_ids = {"connection-1", "game-1"}

        response = await server._handle_message(
            '{"type":"close_session","seq":9,"session_id":"game-1"}',
            "connection-1",
            session_ids,
        )

        self.assertEqual(
            response,
            {"type": "close_session", "seq": 9, "closed": True},
        )
        self.assertEqual(server._service.closed_session_ids, ["game-1"])
        self.assertEqual(session_ids, {"connection-1"})


if __name__ == "__main__":
    unittest.main()
