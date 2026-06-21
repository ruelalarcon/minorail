from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from contracts.observed_snapshot import ObservedSnapshot
from contracts.suggestion_status import SuggestionStatus
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.game.state import GameState
from suggestion.derived_state import DerivedState


class TransitionType(Enum):
    Initial = "initial"
    Unchanged = "unchanged"
    ExpectedAdvance = "expected_advance"
    BoardOnlyCorrection = "board_only_correction"
    SamePiecesChanged = "same_pieces_changed"
    ExpectedAdvanceWithBoardCorrection = "expected_advance_with_board_correction"
    ExpectedAdvanceChanged = "expected_advance_changed"
    UnexpectedPieces = "unexpected_pieces"


class PieceStreamAction(Enum):
    Initialize = "initialize"
    Keep = "keep"
    Append = "append"
    Realign = "realign"


class ReconciliationReason(Enum):
    BoardChangedSamePieceStream = "board_changed_same_piece_stream"
    BoardChangedAfterExpectedAdvance = "board_changed_after_expected_advance"
    PieceStreamChangedUnexpectedly = "piece_stream_changed_unexpectedly"
    RulesChanged = "rules_changed"


@dataclass
class ExpectedAdvance:
    snapshot: ObservedSnapshot
    state: GameState
    new_pieces: list[Piece]


@dataclass
class SessionTransition:
    transition_type: TransitionType
    status: SuggestionStatus
    piece_stream_action: PieceStreamAction
    expected: Optional[ExpectedAdvance] = None
    reconciliation_reason: Optional[ReconciliationReason] = None


def classify_transition(
    shadow_observed: Optional[ObservedSnapshot],
    incoming: ObservedSnapshot,
    previous_suggestion: Optional[Placement],
    derived_state: DerivedState,
    rules: Rules,
) -> SessionTransition:
    if shadow_observed is None:
        return SessionTransition(
            transition_type=TransitionType.Initial,
            status=SuggestionStatus.Synced,
            piece_stream_action=PieceStreamAction.Initialize,
        )

    if incoming.physically_equals(shadow_observed):
        return SessionTransition(
            transition_type=TransitionType.Unchanged,
            status=SuggestionStatus.Synced,
            piece_stream_action=PieceStreamAction.Keep,
        )

    expected = expected_piece_advance(
        shadow_observed, incoming, previous_suggestion, derived_state, rules
    )
    if expected is not None and incoming.physically_equals(expected.snapshot):
        return SessionTransition(
            transition_type=TransitionType.ExpectedAdvance,
            status=SuggestionStatus.Advanced,
            piece_stream_action=PieceStreamAction.Append,
            expected=expected,
        )

    if same_state_except_board(incoming, shadow_observed):
        return SessionTransition(
            transition_type=TransitionType.BoardOnlyCorrection,
            status=SuggestionStatus.Reconciled,
            piece_stream_action=PieceStreamAction.Keep,
            reconciliation_reason=ReconciliationReason.BoardChangedSamePieceStream,
        )

    if observed_pieces(incoming) == observed_pieces(shadow_observed):
        return SessionTransition(
            transition_type=TransitionType.SamePiecesChanged,
            status=SuggestionStatus.Reset,
            piece_stream_action=PieceStreamAction.Keep,
            reconciliation_reason=ReconciliationReason.BoardChangedSamePieceStream,
        )

    if expected is not None and same_state_except_board(incoming, expected.snapshot):
        return SessionTransition(
            transition_type=TransitionType.ExpectedAdvanceWithBoardCorrection,
            status=SuggestionStatus.Reconciled,
            piece_stream_action=PieceStreamAction.Append,
            expected=expected,
            reconciliation_reason=ReconciliationReason.BoardChangedAfterExpectedAdvance,
        )

    if expected is not None:
        return SessionTransition(
            transition_type=TransitionType.ExpectedAdvanceChanged,
            status=SuggestionStatus.Reset,
            piece_stream_action=PieceStreamAction.Append,
            expected=expected,
            reconciliation_reason=ReconciliationReason.BoardChangedAfterExpectedAdvance,
        )

    return SessionTransition(
        transition_type=TransitionType.UnexpectedPieces,
        status=SuggestionStatus.Reset,
        piece_stream_action=PieceStreamAction.Realign,
        reconciliation_reason=ReconciliationReason.PieceStreamChangedUnexpectedly,
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


def same_state_except_board(
    incoming: ObservedSnapshot, shadow_observed: ObservedSnapshot
) -> bool:
    return (
        incoming.board.cols != shadow_observed.board.cols
        and incoming.active == shadow_observed.active
        and incoming.queue == shadow_observed.queue
        and incoming.hold == shadow_observed.hold
        and incoming.can_hold == shadow_observed.can_hold
    )


def _is_prefix(prefix: list[Piece], values: list[Piece]) -> bool:
    return len(values) >= len(prefix) and values[: len(prefix)] == prefix
