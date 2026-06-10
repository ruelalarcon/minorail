from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules

if TYPE_CHECKING:
    from suggestion.contracts.piece_stream_snapshot import PieceStreamSnapshot


@dataclass
class BotCapabilities:
    randomizers: Optional[list[str]] = None
    kicksets: Optional[list[str]] = None
    rot180: bool = False
    sonic_drop: Optional[list[str]] = None
    piece_stream: bool = False
    spawn_position: bool = False

    @staticmethod
    def from_sbp(value: object) -> "BotCapabilities":
        if not isinstance(value, dict):
            return BotCapabilities()
        return BotCapabilities(
            randomizers=_string_list(value.get("randomizers")),
            kicksets=_string_list(value.get("kicksets")),
            rot180=value.get("rot180") is True,
            sonic_drop=_string_list(value.get("sonic_drop")),
            piece_stream=value.get("piece_stream") is True,
            spawn_position=value.get("spawn_position") is True,
        )

    def validate_rules(self, rules: Rules) -> Optional[str]:
        if self.randomizers is not None and rules.randomizer not in self.randomizers:
            return (
                f"bot does not support randomizer {rules.randomizer!r}; "
                f"supported: {', '.join(self.randomizers) or 'none'}"
            )
        if self.kicksets is not None and rules.kickset not in self.kicksets:
            return (
                f"bot does not support kickset {rules.kickset!r}; "
                f"supported: {', '.join(self.kicksets) or 'none'}"
            )
        if rules.rot180 and not self.rot180:
            return "bot does not support rot180"
        if self.sonic_drop is not None and rules.sonic_drop not in self.sonic_drop:
            return (
                f"bot does not support sonic_drop {rules.sonic_drop!r}; "
                f"supported: {', '.join(self.sonic_drop) or 'none'}"
            )
        if (rules.spawn_x, rules.spawn_y) != (4, 19) and not self.spawn_position:
            return "bot does not support custom spawn_position"
        return None


def _string_list(value: object) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, str)]


@dataclass
class MsgRules:
    randomizer: Optional[str] = None
    kickset: Optional[str] = None
    rot180: Optional[bool] = None
    sonic_drop: Optional[str] = None
    allspin_b2b: Optional[bool] = None
    allclear_b2b: Optional[bool] = None
    spawn_x: Optional[int] = None
    spawn_y: Optional[int] = None


@dataclass
class MsgStart:
    board: Board
    active: Piece
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    piece_stream: Optional["PieceStreamSnapshot"] = None


@dataclass
class MsgPlay:
    move: Placement


@dataclass
class MsgNewPiece:
    piece: Piece


@dataclass
class MsgSuggest:
    pass


@dataclass
class MsgStop:
    pass


@dataclass
class MsgQuit:
    pass
