from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.game.state import GameState
from suggestion.derived_state import DerivedState
from suggestion.contracts.observed_snapshot import ObservedSnapshot
from suggestion.contracts.suggestion_status import SuggestionStatus


class BotAction(Enum):
    Start = "start"
    Keep = "keep"
    Advance = "advance"
    Reset = "reset"


class PieceStreamAction(Enum):
    Initialize = "initialize"
    Keep = "keep"
    Append = "append"
    Resync = "resync"


class ResyncType(Enum):
    BoardChangedSamePieceStream = "board_changed_same_piece_stream"
    BoardChangedAfterExpectedAdvance = "board_changed_after_expected_advance"
    PieceStreamChangedUnexpectedly = "piece_stream_changed_unexpectedly"


@dataclass
class ExpectedAdvance:
    snapshot: ObservedSnapshot
    state: GameState
    new_pieces: list[Piece]


@dataclass
class SessionTransition:
    status: SuggestionStatus
    bot_action: BotAction
    piece_stream_action: PieceStreamAction
    expected: Optional[ExpectedAdvance] = None
    resync_type: Optional[ResyncType] = None


def classify_transition(
    shadow_observed: Optional[ObservedSnapshot],
    incoming: ObservedSnapshot,
    previous_suggestion: Optional[Placement],
    derived_state: DerivedState,
    rules: Rules,
) -> SessionTransition:
    if shadow_observed is None:
        return SessionTransition(
            status=SuggestionStatus.Synced,
            bot_action=BotAction.Start,
            piece_stream_action=PieceStreamAction.Initialize,
        )

    if incoming.physically_equals(shadow_observed):
        return SessionTransition(
            status=SuggestionStatus.Synced,
            bot_action=BotAction.Keep,
            piece_stream_action=PieceStreamAction.Keep,
        )

    expected = expected_piece_advance(
        shadow_observed, incoming, previous_suggestion, derived_state, rules
    )
    if expected is not None and incoming.physically_equals(expected.snapshot):
        return SessionTransition(
            status=SuggestionStatus.Advanced,
            bot_action=BotAction.Advance,
            piece_stream_action=PieceStreamAction.Append,
            expected=expected,
        )

    if observed_pieces(incoming) == observed_pieces(shadow_observed):
        return SessionTransition(
            status=SuggestionStatus.Resynced,
            bot_action=BotAction.Reset,
            piece_stream_action=PieceStreamAction.Keep,
            resync_type=ResyncType.BoardChangedSamePieceStream,
        )

    if expected is not None:
        return SessionTransition(
            status=SuggestionStatus.Resynced,
            bot_action=BotAction.Reset,
            piece_stream_action=PieceStreamAction.Append,
            expected=expected,
            resync_type=ResyncType.BoardChangedAfterExpectedAdvance,
        )

    return SessionTransition(
        status=SuggestionStatus.Resynced,
        bot_action=BotAction.Reset,
        piece_stream_action=PieceStreamAction.Resync,
        resync_type=ResyncType.PieceStreamChangedUnexpectedly,
    )


def expected_piece_advance(
    shadow_observed: Optional[ObservedSnapshot],
    incoming: ObservedSnapshot,
    previous_suggestion: Optional[Placement],
    derived_state: DerivedState,
    rules: Rules,
) -> Optional[ExpectedAdvance]:
    if shadow_observed is None or previous_suggestion is None:
        return None

    state = derived_state.to_game_state(shadow_observed)
    if not state.apply_move(previous_suggestion, rules):
        return None

    expected_queue = list(state.queue)
    if not _is_prefix(expected_queue, incoming.queue):
        return None
    new_pieces = incoming.queue[len(expected_queue) :]
    state.queue.extend(new_pieces)

    expected = ObservedSnapshot(
        board=state.board.copy(),
        active=state.active,
        queue=list(state.queue),
        hold=state.hold,
        can_hold=True,
        seq=incoming.seq,
        last_move=previous_suggestion,
    )
    if observed_pieces(incoming) != observed_pieces(expected):
        return None
    return ExpectedAdvance(snapshot=expected, state=state, new_pieces=new_pieces)


def observed_pieces(snapshot: ObservedSnapshot) -> list[Piece]:
    return [snapshot.active.piece, *snapshot.queue]


def _is_prefix(prefix: list[Piece], values: list[Piece]) -> bool:
    return len(values) >= len(prefix) and values[: len(prefix)] == prefix
