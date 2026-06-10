from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import replace
from typing import Any

from tetris.game.state import spawn_location
from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.movegen.steps import MoveStep
from suggestion.bot_session import BotStartupError
from suggestion.contracts.observed_snapshot import ObservedSnapshot
from suggestion.contracts.suggestion_request import SuggestionRequest
from suggestion.contracts.suggestion_result import SuggestionResult
from suggestion.suggestion_service import SuggestionService


class WebSocketApiError(ValueError):
    def __init__(self, reason: str, message: str, seq: int | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.seq = seq


class SuggestionWebSocketServer:
    def __init__(
        self,
        bot_path: str,
        *,
        settings: dict[str, Any],
        bot_args: list[str] | None = None,
        host: str = "127.0.0.1",
        port: int = 8444,
    ) -> None:
        protocol_cfg = settings.get("protocol", {})
        protocol_start_cfg = protocol_cfg.get("start", {})
        logging_cfg = settings.get("logging", {})
        bot_info_cfg = logging_cfg.get("bot_info", {})
        self._service = SuggestionService(
            bot_path,
            bot_args=bot_args,
            piece_stream_limit=protocol_start_cfg.get("piece_stream_limit", 11),
            info_print_topics=bot_info_cfg.get("print", ["warning"]),
        )
        service_path_cfg = settings.get("service", {}).get("path", {})
        self._convert_sonic_drops = service_path_cfg.get("convert_sonic_drops", False)
        self._timeout_ms = settings.get("bot", {}).get("suggest_timeout_ms", 10_000)
        self._rules = Rules.from_settings(settings)
        self._host = host
        self._port = port
        self._lock = asyncio.Lock()

    async def serve_forever(self) -> None:
        try:
            from websockets.asyncio.server import serve
        except ImportError as e:
            raise RuntimeError("websocket API requires the 'websockets' package") from e

        async with serve(self._handle_connection, self._host, self._port):
            print(
                f"[info] websocket API listening on ws://{self._host}:{self._port}",
                file=sys.stderr,
            )
            await asyncio.Future()

    def close(self) -> None:
        self._service.close()

    async def _handle_connection(self, websocket: Any) -> None:
        connection_session_id = f"ws-{uuid.uuid4()}"
        session_ids = {connection_session_id}
        try:
            async for message in websocket:
                response = await self._handle_message(
                    message, connection_session_id, session_ids
                )
                await websocket.send(json.dumps(response, separators=(",", ":")))
        finally:
            for session_id in session_ids:
                self._service.close_session(session_id)

    async def _handle_message(
        self, message: object, connection_session_id: str, session_ids: set[str]
    ) -> dict[str, Any]:
        seq = None
        try:
            if not isinstance(message, str):
                raise WebSocketApiError(
                    "invalid_request", "message must be a JSON text frame"
                )
            try:
                obj = json.loads(message)
            except json.JSONDecodeError as e:
                raise WebSocketApiError(
                    "invalid_request", "message must be valid JSON"
                ) from e
            if not isinstance(obj, dict):
                raise WebSocketApiError(
                    "invalid_request", "message must be a JSON object"
                )
            seq = _optional_seq(obj.get("seq"))
            request = request_from_json(
                obj,
                base_rules=self._rules,
                default_session_id=connection_session_id,
                default_timeout_ms=self._timeout_ms,
                default_convert_sonic_drops=self._convert_sonic_drops,
            )
            session_ids.add(request.session_id)
            async with self._lock:
                result = await asyncio.to_thread(self._service.suggest, request)
            return result_to_json(result)
        except WebSocketApiError as e:
            return error_to_json(e)
        except BotStartupError as e:
            return error_to_json(
                WebSocketApiError("bot_startup_failed", str(e), seq=seq)
            )
        except Exception as e:
            return error_to_json(WebSocketApiError("internal_error", str(e), seq=seq))


def request_from_json(
    obj: dict[str, Any],
    *,
    base_rules: Rules,
    default_session_id: str = "default",
    default_timeout_ms: int = 10_000,
    default_convert_sonic_drops: bool = False,
) -> SuggestionRequest:
    if obj.get("type", "suggest") != "suggest":
        raise WebSocketApiError(
            "invalid_request",
            "type must be 'suggest'",
            seq=_optional_seq(obj.get("seq")),
        )

    seq = _seq(obj.get("seq"))
    rules = _rules(obj.get("rules"), base_rules)
    active = _piece(obj.get("active"), "active")
    queue = _piece_list(obj.get("queue", []), "queue")
    hold_raw = obj.get("hold")
    hold = None if hold_raw is None else _piece(hold_raw, "hold")
    snapshot = ObservedSnapshot(
        board=_board(obj.get("board")),
        active=spawn_location(active, x=rules.spawn_x, y=rules.spawn_y),
        queue=queue,
        hold=hold,
        can_hold=_bool(obj.get("can_hold", True), "can_hold"),
        seq=seq,
        last_move=_optional_placement(obj.get("last_move"), "last_move"),
    )
    return SuggestionRequest(
        snapshot=snapshot,
        rules=rules,
        include_path=_bool(obj.get("include_path", True), "include_path"),
        convert_sonic_drops=_bool(
            obj.get("convert_sonic_drops", default_convert_sonic_drops),
            "convert_sonic_drops",
        ),
        session_id=_session_id(obj.get("session_id"), default_session_id),
        timeout_ms=_timeout_ms(obj.get("timeout_ms"), default_timeout_ms),
    )


def result_to_json(result: SuggestionResult) -> dict[str, Any]:
    return {
        "type": "suggestion",
        "seq": result.seq,
        "status": result.status.value,
        "placements": [_placement(p) for p in result.placements],
        "placement": _optional_output_placement(result.placement),
        "path": None if result.path is None else [_step(step) for step in result.path],
        "reason": result.reason,
    }


def error_to_json(error: WebSocketApiError) -> dict[str, Any]:
    return {
        "type": "error",
        "seq": error.seq,
        "reason": error.reason,
        "message": error.message,
    }


def _board(value: object) -> Board:
    if isinstance(value, dict):
        cols = value.get("cols")
        if not isinstance(cols, list) or len(cols) != 10:
            raise WebSocketApiError(
                "invalid_request", "board.cols must be a list of 10 integers"
            )
        parsed_cols: list[int] = []
        for i, col in enumerate(cols):
            if isinstance(col, bool) or not isinstance(col, int):
                raise WebSocketApiError(
                    "invalid_request", f"board.cols[{i}] must be an integer"
                )
            if col < 0 or col >= (1 << 40):
                raise WebSocketApiError(
                    "invalid_request", f"board.cols[{i}] must fit in 40 bits"
                )
            parsed_cols.append(col)
        return Board(cols=parsed_cols)
    if isinstance(value, list):
        if len(value) != 40:
            raise WebSocketApiError(
                "invalid_request", "SBP board matrix must contain 40 rows"
            )
        for y, row in enumerate(value):
            if not isinstance(row, list) or len(row) != 10:
                raise WebSocketApiError(
                    "invalid_request", f"SBP board row {y} must contain 10 cells"
                )
        return Board.from_sbp(value)
    raise WebSocketApiError(
        "invalid_request", "board must be {'cols': [...]} or an SBP row matrix"
    )


def _seq(value: object) -> int:
    seq = _optional_seq(value)
    if seq is None:
        raise WebSocketApiError("invalid_request", "seq must be an integer")
    return seq


def _optional_seq(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise WebSocketApiError("invalid_request", "seq must be an integer")
    if value < 0:
        raise WebSocketApiError("invalid_request", "seq must be non-negative", value)
    return value


def _piece(value: object, field: str) -> Piece:
    if not isinstance(value, str):
        raise WebSocketApiError("invalid_request", f"{field} must be a piece string")
    try:
        return Piece(value)
    except ValueError as e:
        raise WebSocketApiError(
            "invalid_request", f"{field} must be one of I, O, T, L, J, S, Z"
        ) from e


def _piece_list(value: object, field: str) -> list[Piece]:
    if not isinstance(value, list):
        raise WebSocketApiError("invalid_request", f"{field} must be a list")
    return [_piece(item, f"{field}[{i}]") for i, item in enumerate(value)]


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise WebSocketApiError("invalid_request", f"{field} must be a boolean")
    return value


def _session_id(value: object, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or value == "":
        raise WebSocketApiError(
            "invalid_request", "session_id must be a non-empty string"
        )
    return value


def _timeout_ms(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise WebSocketApiError("invalid_request", "timeout_ms must be an integer")
    if value <= 0:
        raise WebSocketApiError("invalid_request", "timeout_ms must be positive")
    return value


def _optional_placement(value: object, field: str) -> Placement | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise WebSocketApiError("invalid_request", f"{field} must be an object")
    try:
        return Placement.from_sbp(value)
    except (KeyError, TypeError, ValueError) as e:
        raise WebSocketApiError(
            "invalid_request", f"{field} must be an SBP placement"
        ) from e


def _rules(value: object, base_rules: Rules) -> Rules:
    if value is None:
        return base_rules
    if not isinstance(value, dict):
        raise WebSocketApiError("invalid_request", "rules must be an object")

    allowed = {
        "randomizer",
        "kickset",
        "rot180",
        "sonic_drop",
        "allspin_b2b",
        "allclear_b2b",
        "spawn_x",
        "spawn_y",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise WebSocketApiError(
            "invalid_request", f"unknown rules field: {', '.join(unknown)}"
        )

    updates: dict[str, object] = {}
    for field in ("randomizer", "kickset", "sonic_drop"):
        if field in value:
            if not isinstance(value[field], str):
                raise WebSocketApiError(
                    "invalid_request", f"rules.{field} must be a string"
                )
            updates[field] = value[field]
    for field in ("rot180", "allspin_b2b", "allclear_b2b"):
        if field in value:
            updates[field] = _bool(value[field], f"rules.{field}")
    for field in ("spawn_x", "spawn_y"):
        if field in value:
            updates[field] = _int(value[field], f"rules.{field}")
    return replace(base_rules, **updates)


def _int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WebSocketApiError("invalid_request", f"{field} must be an integer")
    return value


def _optional_output_placement(value: Placement | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return _placement(value)


def _placement(value: Placement) -> dict[str, Any]:
    return value.to_sbp()


def _step(value: MoveStep) -> str:
    return value.value
