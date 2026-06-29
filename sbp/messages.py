from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from tetris.model.board import Board
from tetris.model.back_to_back_source import BackToBackSource
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.model.spin_detection import SpinDetection

if TYPE_CHECKING:
    from contracts.piece_stream_snapshot import PieceStreamSnapshot


@dataclass(frozen=True)
class IntRange:
    min: int
    max: int

    @staticmethod
    def from_sbp(value: object) -> "IntRange | None":
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return IntRange(value, value)
        if not isinstance(value, dict):
            return None
        min_value = value.get("min")
        max_value = value.get("max")
        if isinstance(min_value, bool) or isinstance(max_value, bool):
            return None
        if not isinstance(min_value, int) or not isinstance(max_value, int):
            return None
        if min_value > max_value:
            return None
        return IntRange(min_value, max_value)

    def contains(self, value: int) -> bool:
        return self.min <= value <= self.max

    def label(self) -> str:
        return str(self.min) if self.min == self.max else f"{self.min}..{self.max}"


@dataclass(frozen=True)
class BoardSizeCapability:
    width: IntRange
    height: IntRange

    @staticmethod
    def from_sbp(value: object) -> "BoardSizeCapability | None":
        if not isinstance(value, dict):
            return None
        width = IntRange.from_sbp(value.get("width"))
        height = IntRange.from_sbp(value.get("height"))
        if width is None or height is None:
            return None
        return BoardSizeCapability(width=width, height=height)


@dataclass
class BotCapabilities:
    randomizers: Optional[list[str]] = None
    kicksets: Optional[list[str]] = None
    rot180: bool = False
    sonic_drop: Optional[list[str]] = None
    spin_detection: Optional[list[str]] = None
    back_to_back_sources: Optional[list[str]] = None
    piece_stream: bool = False
    spawn_position: bool = False
    board: bool = False
    board_size: BoardSizeCapability | None = None

    @staticmethod
    def from_sbp(value: object) -> "BotCapabilities":
        if not isinstance(value, dict):
            return BotCapabilities()
        return BotCapabilities(
            randomizers=_string_list(value.get("randomizers")),
            kicksets=_string_list(value.get("kicksets")),
            rot180=value.get("rot180") is True,
            sonic_drop=_string_list(value.get("sonic_drop")),
            spin_detection=_string_list(value.get("spin_detection")),
            back_to_back_sources=_string_list(value.get("back_to_back_sources")),
            piece_stream=value.get("piece_stream") is True,
            spawn_position=value.get("spawn_position") is True,
            board=value.get("board") is True,
            board_size=BoardSizeCapability.from_sbp(value.get("board_size")),
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
        if (
            self.spin_detection is not None
            and rules.spin_detection.value not in self.spin_detection
        ):
            return (
                f"bot does not support spin_detection {rules.spin_detection.value!r}; "
                f"supported: {', '.join(self.spin_detection) or 'none'}"
            )
        if self.back_to_back_sources is not None:
            supported = set(self.back_to_back_sources)
            requested = {source.value for source in rules.back_to_back_sources}
            unsupported = sorted(requested - supported)
            if unsupported:
                return (
                    "bot does not support back_to_back_sources "
                    f"{', '.join(unsupported)!r}; supported: "
                    f"{', '.join(self.back_to_back_sources) or 'none'}"
                )
        if (rules.spawn_x, rules.spawn_y) != (4, 20) and not self.spawn_position:
            return "bot does not support custom spawn_position"
        if self.board_size is None:
            if (rules.board_width, rules.board_height) != (10, 40):
                return "bot does not support custom board_size"
        else:
            if not self.board_size.width.contains(rules.board_width):
                return (
                    f"bot does not support board_size.width {rules.board_width}; "
                    f"supported: {self.board_size.width.label()}"
                )
            if not self.board_size.height.contains(rules.board_height):
                return (
                    f"bot does not support board_size.height {rules.board_height}; "
                    f"supported: {self.board_size.height.label()}"
                )
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
    spin_detection: Optional[SpinDetection | str] = None
    back_to_back_sources: Optional[frozenset[BackToBackSource] | list[str]] = None
    spawn_position: Optional[dict[str, int]] = None
    board_size: Optional[dict[str, int]] = None


@dataclass
class MsgStart:
    board: Board
    active: Piece
    queue: list[Piece]
    hold: Optional[Piece]
    combo: int
    back_to_back: int
    piece_stream: Optional["PieceStreamSnapshot"] = None
    incoming_garbage: list[int] | None = None
    extensions: dict[str, Any] | None = None


@dataclass
class MsgBoard:
    board: Board


@dataclass
class MsgAdvance:
    move: Placement


@dataclass
class MsgNewPiece:
    piece: Piece


@dataclass
class MsgSuggest:
    incoming_garbage: list[int] | None = None
    extensions: dict[str, Any] | None = None


@dataclass
class MsgStop:
    pass


@dataclass
class MsgQuit:
    pass
