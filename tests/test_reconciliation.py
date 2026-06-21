from __future__ import annotations

import unittest

from contracts.suggestion_status import SuggestionStatus
from suggestion.session.reconciliation import (
    ReconciliationAction,
    ReconciliationStep,
    choose_reconciliation,
)
from suggestion.session.transition import (
    PieceStreamAction,
    ReconciliationReason,
    SessionTransition,
    TransitionType,
)


def transition(
    transition_type: TransitionType,
    *,
    status: SuggestionStatus = SuggestionStatus.Reconciled,
    piece_stream_action: PieceStreamAction = PieceStreamAction.Keep,
    reconciliation_reason: ReconciliationReason
    | None = ReconciliationReason.BoardChangedSamePieceStream,
) -> SessionTransition:
    return SessionTransition(
        transition_type=transition_type,
        status=status,
        piece_stream_action=piece_stream_action,
        reconciliation_reason=reconciliation_reason,
    )


class ReconciliationTests(unittest.TestCase):
    def test_board_only_uses_board_when_supported(self) -> None:
        reconciliation = choose_reconciliation(
            transition(TransitionType.BoardOnlyCorrection),
            rules_changed=False,
            supports_board=True,
        )

        self.assertEqual(reconciliation.action, ReconciliationAction.Board)
        self.assertEqual(reconciliation.steps, (ReconciliationStep.Board,))
        self.assertEqual(reconciliation.status, SuggestionStatus.Reconciled)

    def test_board_only_resets_without_board_support(self) -> None:
        reconciliation = choose_reconciliation(
            transition(TransitionType.BoardOnlyCorrection),
            rules_changed=False,
            supports_board=False,
        )

        self.assertEqual(reconciliation.action, ReconciliationAction.Reset)
        self.assertEqual(reconciliation.steps, (ReconciliationStep.Reset,))
        self.assertEqual(reconciliation.status, SuggestionStatus.Reset)

    def test_expected_advance_with_board_correction_advances_then_boards(self) -> None:
        reconciliation = choose_reconciliation(
            transition(TransitionType.ExpectedAdvanceWithBoardCorrection),
            rules_changed=False,
            supports_board=True,
        )

        self.assertEqual(reconciliation.action, ReconciliationAction.AdvanceThenBoard)
        self.assertEqual(
            reconciliation.steps,
            (ReconciliationStep.Advance, ReconciliationStep.Board),
        )
        self.assertEqual(reconciliation.status, SuggestionStatus.Reconciled)

    def test_expected_advance_with_board_correction_resets_without_support(
        self,
    ) -> None:
        reconciliation = choose_reconciliation(
            transition(TransitionType.ExpectedAdvanceWithBoardCorrection),
            rules_changed=False,
            supports_board=False,
        )

        self.assertEqual(reconciliation.action, ReconciliationAction.Reset)
        self.assertEqual(reconciliation.steps, (ReconciliationStep.Reset,))
        self.assertEqual(reconciliation.status, SuggestionStatus.Reset)

    def test_rules_change_resets(self) -> None:
        reconciliation = choose_reconciliation(
            transition(
                TransitionType.ExpectedAdvanceWithBoardCorrection,
                reconciliation_reason=ReconciliationReason.RulesChanged,
            ),
            rules_changed=True,
            supports_board=True,
        )

        self.assertEqual(reconciliation.action, ReconciliationAction.Reset)
        self.assertEqual(reconciliation.steps, (ReconciliationStep.Reset,))
        self.assertEqual(reconciliation.status, SuggestionStatus.Reset)

    def test_unexpected_pieces_reset(self) -> None:
        reconciliation = choose_reconciliation(
            transition(TransitionType.UnexpectedPieces),
            rules_changed=False,
            supports_board=True,
        )

        self.assertEqual(reconciliation.action, ReconciliationAction.Reset)
        self.assertEqual(reconciliation.steps, (ReconciliationStep.Reset,))
        self.assertEqual(reconciliation.status, SuggestionStatus.Reset)


if __name__ == "__main__":
    unittest.main()
