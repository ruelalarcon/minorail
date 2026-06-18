from __future__ import annotations

from typing import Any

from sbp.messages import (
    MsgNewPiece,
    MsgPlay,
    MsgQuit,
    MsgRules,
    MsgStart,
    MsgStop,
    MsgSuggest,
)
from tetris.model.board import Board
from tetris.model.rules import Rules

OutboundMessage = (
    MsgRules | MsgStart | MsgPlay | MsgNewPiece | MsgSuggest | MsgStop | MsgQuit
)


def rules_message(rules: Rules) -> MsgRules:
    return MsgRules(
        randomizer=rules.randomizer,
        kickset=rules.kickset,
        rot180=rules.rot180,
        sonic_drop=rules.sonic_drop,
        allspin_b2b=rules.allspin_b2b,
        allclear_b2b=rules.allclear_b2b,
        spawn_x=rules.spawn_x,
        spawn_y=rules.spawn_y,
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
                    "allspin_b2b": message.allspin_b2b,
                    "allclear_b2b": message.allclear_b2b,
                    "spawn_x": message.spawn_x,
                    "spawn_y": message.spawn_y,
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
            if message.extensions is not None:
                obj["extensions"] = message.extensions
            return obj
        case MsgPlay():
            return {"type": "play", "move": message.move.to_sbp()}
        case MsgNewPiece():
            return {"type": "new_piece", "piece": message.piece.value}
        case MsgSuggest():
            obj = {"type": "suggest"}
            if message.extensions is not None:
                obj["extensions"] = message.extensions
            return obj
        case MsgStop():
            return {"type": "stop"}
        case MsgQuit():
            return {"type": "quit"}


def board_to_sbp(board: Board) -> list[list[str | None]]:
    rows: list[list[str | None]] = [[None] * 10 for _ in range(40)]
    for x in range(10):
        for y in range(40):
            if board.cols[x] & (1 << y):
                rows[y][x] = "G"
    return rows


def _without_none(obj: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in obj.items() if value is not None}
