from __future__ import annotations

import json
from typing import Optional

from core.board import Board
from core.piece import Piece
from core.placement import Placement
from tbp.messages import (
    MsgNewPiece,
    MsgPlay,
    MsgQuit,
    MsgRules,
    MsgStart,
    MsgStop,
    MsgSuggest,
)

FrontendMessage = (
    MsgRules | MsgStart | MsgPlay | MsgNewPiece | MsgSuggest | MsgStop | MsgQuit
)


def parse(line: str) -> Optional[FrontendMessage]:
    """Parse a JSON line from a bot into a frontend message. Returns None for unknown types."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    match obj.get("type"):
        case "rules":
            return MsgRules(randomizer=obj.get("randomizer"))
        case "start":
            hold_raw = obj.get("hold")
            return MsgStart(
                board=Board.from_tbp(obj.get("board", [])),
                queue=[Piece(p) for p in obj.get("queue", [])],
                hold=Piece(hold_raw) if hold_raw is not None else None,
                combo=obj.get("combo", 0),
                back_to_back=obj.get("back_to_back", False),
            )
        case "play":
            return MsgPlay(move=Placement.from_tbp(obj["move"]))
        case "new_piece":
            return MsgNewPiece(piece=Piece(obj["piece"]))
        case "suggest":
            return MsgSuggest()
        case "stop":
            return MsgStop()
        case "quit":
            return MsgQuit()
        case _:
            return None
