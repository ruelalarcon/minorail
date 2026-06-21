from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from contracts.suggestion_status import SuggestionStatus
from suggestion.session.transition import SessionTransition, TransitionType


class ReconciliationAction(Enum):
    Start = "start"
    Keep = "keep"
    Advance = "advance"
    Board = "board"
    AdvanceThenBoard = "advance_then_board"
    Reset = "reset"


class ReconciliationStep(Enum):
    Start = "start"
    Advance = "advance"
    Board = "board"
    Reset = "reset"


@dataclass(frozen=True)
class Reconciliation:
    action: ReconciliationAction
    steps: tuple[ReconciliationStep, ...]
    status: SuggestionStatus


def choose_reconciliation(
    transition: SessionTransition,
    *,
    rules_changed: bool,
    supports_board: bool,
) -> Reconciliation:
    if rules_changed:
        return Reconciliation(
            ReconciliationAction.Reset,
            (ReconciliationStep.Reset,),
            SuggestionStatus.Reset,
        )

    match transition.transition_type:
        case TransitionType.Initial:
            return Reconciliation(
                ReconciliationAction.Start,
                (ReconciliationStep.Start,),
                SuggestionStatus.Synced,
            )
        case TransitionType.Unchanged:
            return Reconciliation(
                ReconciliationAction.Keep, (), SuggestionStatus.Synced
            )
        case TransitionType.ExpectedAdvance:
            return Reconciliation(
                ReconciliationAction.Advance,
                (ReconciliationStep.Advance,),
                SuggestionStatus.Advanced,
            )
        case TransitionType.BoardOnlyCorrection:
            if supports_board:
                return Reconciliation(
                    ReconciliationAction.Board,
                    (ReconciliationStep.Board,),
                    SuggestionStatus.Reconciled,
                )
            return Reconciliation(
                ReconciliationAction.Reset,
                (ReconciliationStep.Reset,),
                SuggestionStatus.Reset,
            )
        case TransitionType.ExpectedAdvanceWithBoardCorrection:
            if supports_board:
                return Reconciliation(
                    ReconciliationAction.AdvanceThenBoard,
                    (ReconciliationStep.Advance, ReconciliationStep.Board),
                    SuggestionStatus.Reconciled,
                )
            return Reconciliation(
                ReconciliationAction.Reset,
                (ReconciliationStep.Reset,),
                SuggestionStatus.Reset,
            )
        case (
            TransitionType.SamePiecesChanged
            | TransitionType.ExpectedAdvanceChanged
            | TransitionType.UnexpectedPieces
        ):
            return Reconciliation(
                ReconciliationAction.Reset,
                (ReconciliationStep.Reset,),
                SuggestionStatus.Reset,
            )
