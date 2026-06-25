from __future__ import annotations

from typing import Any

from sbp.messages import (
    MsgBoard,
    MsgNewPiece,
    MsgPlay,
    MsgQuit,
    MsgRules,
    MsgStart,
    MsgStop,
    MsgSuggest,
)
from tetris.model.board import Board, cell_label
from tetris.model.rules import Rules

OutboundMessage = (
    MsgRules
    | MsgStart
    | MsgBoard
    | MsgPlay
    | MsgNewPiece
    | MsgSuggest
    | MsgStop
    | MsgQuit
)


def rules_message(rules: Rules) -> MsgRules:
    return MsgRules(
        randomizer=rules.randomizer,
        kickset=rules.kickset,
        rot180=rules.rot180,
        sonic_drop=rules.sonic_drop,
        spin_detection=rules.spin_detection,
        back_to_back_sources=rules.back_to_back_sources,
        spawn_position={"x": rules.spawn_x, "y": rules.spawn_y},
        board_size={"width": rules.board_width, "height": rules.board_height},
    )


def to_jsonable(message: OutboundMessage) -> dict[str, Any]:
    match message:
        case MsgRules():
            return _without_none(
                {
                    "type": "rules",
                    "randomizer": message.randomizer,
                    "kickset": message.kickset,
                    "rot180": message.rot180,
                    "sonic_drop": message.sonic_drop,
                    "spin_detection": _enum_value(message.spin_detection),
                    "back_to_back_sources": _back_to_back_sources(
                        message.back_to_back_sources
                    ),
                    "spawn_position": message.spawn_position,
                    "board_size": message.board_size,
                }
            )
        case MsgStart():
            obj: dict[str, Any] = {
                "type": "start",
                "board": board_to_sbp(message.board),
                "active": message.active.value,
                "queue": [p.value for p in message.queue],
                "hold": message.hold.value if message.hold is not None else None,
                "combo": message.combo,
                "back_to_back": message.back_to_back,
            }
            if message.piece_stream is not None:
                obj["piece_stream"] = {
                    "offset": message.piece_stream.offset,
                    "pieces": [p.value for p in message.piece_stream.pieces],
                }
            if message.incoming_garbage is not None:
                obj["incoming_garbage"] = list(message.incoming_garbage)
            if message.extensions is not None:
                obj["extensions"] = message.extensions
            return obj
        case MsgBoard():
            return {"type": "board", "board": board_to_sbp(message.board)}
        case MsgPlay():
            return {"type": "play", "move": message.move.to_sbp()}
        case MsgNewPiece():
            return {"type": "new_piece", "piece": message.piece.value}
        case MsgSuggest():
            obj = {"type": "suggest"}
            if message.incoming_garbage is not None:
                obj["incoming_garbage"] = list(message.incoming_garbage)
            if message.extensions is not None:
                obj["extensions"] = message.extensions
            return obj
        case MsgStop():
            return {"type": "stop"}
        case MsgQuit():
            return {"type": "quit"}


def board_to_sbp(board: Board) -> list[list[str | None]]:
    rows: list[list[str | None]] = [[None] * board.width for _ in range(board.height)]
    for y in range(board.height):
        for x in range(board.width):
            rows[y][x] = cell_label(board.cell(x, y))
    return rows


def _without_none(obj: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in obj.items() if value is not None}


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _back_to_back_sources(value: Any) -> Any:
    if value is None:
        return None
    return sorted(_enum_value(item) for item in value)
