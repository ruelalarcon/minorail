from __future__ import annotations

import json
from typing import Optional

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from suggestion.contracts.piece_stream_snapshot import PieceStreamSnapshot
from protocols.tbp.messages import (
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


def _counter(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return max(0, value)
    return default


def parse(line: str) -> Optional[FrontendMessage]:
    """Parse a JSON line from a bot into a frontend message. Returns None for unknown types."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    match obj.get("type"):
        case "rules":
            return MsgRules(
                randomizer=obj.get("randomizer"),
                kickset=obj.get("kickset"),
                rot180=obj.get("rot180"),
                sonic_drop=obj.get("sonic_drop"),
                allspin_b2b=obj.get("allspin_b2b"),
                allclear_b2b=obj.get("allclear_b2b"),
                spawn_x=obj.get("spawn_x"),
                spawn_y=obj.get("spawn_y"),
            )
        case "start":
            hold_raw = obj.get("hold")
            queue = [Piece(p) for p in obj.get("queue", [])]
            active_raw = obj.get("active")
            if not isinstance(active_raw, str):
                return None
            active = Piece(active_raw)
            piece_stream_raw = obj.get("piece_stream")
            piece_stream = None
            if isinstance(piece_stream_raw, dict):
                piece_stream = PieceStreamSnapshot(
                    offset=piece_stream_raw.get("offset"),
                    pieces=[Piece(p) for p in piece_stream_raw.get("pieces", [])],
                )
            return MsgStart(
                board=Board.from_tbp(obj.get("board", [])),
                active=active,
                queue=queue,
                hold=Piece(hold_raw) if hold_raw is not None else None,
                combo=_counter(obj.get("combo", 0)),
                back_to_back=_counter(obj.get("back_to_back", 0)),
                piece_stream=piece_stream,
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
