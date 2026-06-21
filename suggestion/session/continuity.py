from __future__ import annotations

import sys
import threading
from typing import Any, Callable, Optional, Protocol

from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.movegen.pathfinder import convert_sonic_drops, find_path
from contracts.bot_snapshot import BotSnapshot
from contracts.observed_snapshot import ObservedSnapshot
from contracts.suggestion_request import SuggestionRequest
from contracts.suggestion_result import SuggestionResult
from contracts.suggestion_status import SuggestionStatus
from suggestion.derived_state import DerivedState
from suggestion.move_selection import moving_piece_for, pick_move
from suggestion.piece_stream_tracker import PieceStreamTracker
from suggestion.session.reconciliation import (
    Reconciliation,
    ReconciliationAction,
    ReconciliationStep,
    choose_reconciliation,
)
from suggestion.session.transition import (
    PieceStreamAction,
    ReconciliationReason,
    SessionTransition,
    TransitionType,
    classify_transition,
    observed_pieces,
)


class BotSessionLike(Protocol):
    def start_from(self, snapshot: BotSnapshot, rules: Rules) -> None: ...

    def suggest(
        self,
        timeout_ms: int,
        incoming_garbage: list[int] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> list[Placement]: ...

    def advance_with(
        self, placement: Placement, new_pieces: list[Piece] | None = None
    ) -> None: ...

    def supports_board_update(self) -> bool: ...

    def update_board(self, snapshot: BotSnapshot, rules: Rules) -> bool: ...

    def reset_from(self, snapshot: BotSnapshot, rules: Rules) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


BotSessionFactory = Callable[[], BotSessionLike]


class SuggestionContinuity:
    def __init__(
        self,
        bot_session_factory: BotSessionFactory,
        piece_stream_limit: int = 11,
        idle_ms: int = 60_000,
    ) -> None:
        self._lock = threading.RLock()
        self._idle_s = idle_ms / 1000
        self._go_idle_timer: threading.Timer | None = None
        self._go_idle_generation = 0
        self._bot_needs_start = False
        self._bot_game_active = False
        self._piece_stream_limit = piece_stream_limit
        self.latest_observed: Optional[ObservedSnapshot] = None
        self.shadow_observed: Optional[ObservedSnapshot] = None
        self.derived_state = DerivedState.neutral()
        self.piece_stream = PieceStreamTracker(piece_stream_limit)
        self.previous_suggestion: Optional[Placement] = None
        self.bot_session: BotSessionLike = bot_session_factory()
        self.rules: Optional[Rules] = None

    def suggest(self, request: SuggestionRequest) -> SuggestionResult:
        with self._lock:
            self._cancel_go_idle()
            try:
                return self._suggest_locked(request)
            finally:
                self._schedule_go_idle()

    def close(self) -> None:
        with self._lock:
            self._cancel_go_idle()
            if self._bot_game_active:
                self.bot_session.stop()
            self.bot_session.close()
            self._bot_game_active = False

    def stop_game(self) -> None:
        with self._lock:
            self._cancel_go_idle()
            if self._bot_game_active:
                self.bot_session.stop()
            self._reset_game_continuity()

    def _suggest_locked(self, request: SuggestionRequest) -> SuggestionResult:
        validation_error = self._validate(request.snapshot, request.rules)
        if validation_error is not None:
            return SuggestionResult(
                seq=request.snapshot.seq,
                status=SuggestionStatus.Invalid,
                placements=[],
                placement=None,
                path=None,
                reason=validation_error,
            )

        transition, reconciliation = self._sync_to_request(request)
        self._apply_reconciliation(reconciliation, transition, request)

        moves = self.bot_session.suggest(
            request.timeout_ms,
            request.incoming_garbage,
            request.extensions,
        )
        chosen = pick_move(moves, request.snapshot)
        if chosen is None:
            self.latest_observed = request.snapshot.copy()
            self.shadow_observed = request.snapshot.copy()
            self.previous_suggestion = None
            return SuggestionResult(
                seq=request.snapshot.seq,
                status=SuggestionStatus.NoSuggestion,
                placements=moves,
                placement=None,
                path=None,
                reason="bot returned no usable placement",
            )

        path = None
        reason = None
        if request.pathfinding:
            moving_piece = moving_piece_for(request.snapshot, chosen)
            if moving_piece is not None:
                path = find_path(
                    request.snapshot.board, moving_piece, chosen.location, request.rules
                )
                if path is not None and request.convert_sonic_drops:
                    path = convert_sonic_drops(
                        path,
                        request.snapshot.board,
                        moving_piece,
                        request.rules.kickset,
                        request.rules.spawn_x,
                        request.rules.spawn_y,
                    )
            if path is None:
                reason = "no path found for selected placement"

        self.latest_observed = request.snapshot.copy()
        self.shadow_observed = request.snapshot.copy()
        self.previous_suggestion = chosen
        self.rules = request.rules
        return SuggestionResult(
            seq=request.snapshot.seq,
            status=reconciliation.status,
            placements=moves,
            placement=chosen,
            path=path,
            reason=reason,
        )

    def _sync_to_request(
        self, request: SuggestionRequest
    ) -> tuple[SessionTransition, Reconciliation]:
        incoming = request.snapshot
        previous_rules = self.rules
        transition_rules = previous_rules or request.rules
        self.rules = request.rules
        transition = classify_transition(
            shadow_observed=self.shadow_observed,
            incoming=incoming,
            previous_suggestion=self.previous_suggestion,
            derived_state=self.derived_state,
            rules=transition_rules,
        )
        rules_changed = previous_rules is not None and previous_rules != request.rules
        if rules_changed:
            transition = SessionTransition(
                transition_type=transition.transition_type,
                status=SuggestionStatus.Reset,
                piece_stream_action=transition.piece_stream_action,
                expected=transition.expected,
                reconciliation_reason=ReconciliationReason.RulesChanged,
            )

        reconciliation = choose_reconciliation(
            transition,
            rules_changed=rules_changed,
            supports_board=self.bot_session.supports_board_update(),
        )

        if transition.reconciliation_reason is not None:
            self._log_reconciliation(transition, reconciliation, incoming)

        if transition.status == SuggestionStatus.Advanced:
            assert transition.expected is not None
            self.derived_state.update_from_confirmed(transition.expected.state)
        elif reconciliation.action == ReconciliationAction.AdvanceThenBoard:
            assert transition.expected is not None
            self.derived_state.update_from_confirmed(transition.expected.state)
        elif transition.status in {
            SuggestionStatus.Reconciled,
            SuggestionStatus.Reset,
        }:
            self.derived_state.reconcile_from(incoming, request.rules)
        elif transition.transition_type == TransitionType.Initial:
            self.derived_state = DerivedState.from_observed(incoming)

        self._apply_piece_stream_action(transition, incoming)
        return transition, reconciliation

    def _apply_piece_stream_action(
        self, transition: SessionTransition, incoming: ObservedSnapshot
    ) -> None:
        match transition.piece_stream_action:
            case PieceStreamAction.Initialize:
                self.piece_stream.initialize(observed_pieces(incoming))
            case PieceStreamAction.Keep:
                pass
            case PieceStreamAction.Append:
                assert transition.expected is not None
                self.piece_stream.append(transition.expected.new_pieces)
            case PieceStreamAction.Realign:
                self.piece_stream.realign(observed_pieces(incoming))

    def _apply_reconciliation(
        self,
        reconciliation: Reconciliation,
        transition: SessionTransition,
        request: SuggestionRequest,
    ) -> None:
        bot_snapshot = self._to_bot_snapshot(request)
        if self._bot_needs_start:
            self.bot_session.start_from(bot_snapshot, request.rules)
            self._bot_game_active = True
            self._bot_needs_start = False
            return

        for step in reconciliation.steps:
            match step:
                case ReconciliationStep.Start:
                    self.bot_session.start_from(bot_snapshot, request.rules)
                    self._bot_game_active = True
                case ReconciliationStep.Advance:
                    self._advance_bot(transition)
                case ReconciliationStep.Board:
                    self.bot_session.update_board(bot_snapshot, request.rules)
                    self._bot_game_active = True
                case ReconciliationStep.Reset:
                    self.bot_session.reset_from(bot_snapshot, request.rules)
                    self._bot_game_active = True

    def _advance_bot(self, transition: SessionTransition) -> None:
        assert self.previous_suggestion is not None
        assert transition.expected is not None
        self.bot_session.advance_with(
            self.previous_suggestion, transition.expected.new_pieces
        )

    def _reset_game_continuity(self) -> None:
        self._bot_game_active = False
        self._bot_needs_start = False
        self.latest_observed = None
        self.shadow_observed = None
        self.derived_state = DerivedState.neutral()
        self.piece_stream = PieceStreamTracker(self._piece_stream_limit)
        self.previous_suggestion = None
        self.rules = None

    def _to_bot_snapshot(self, request: SuggestionRequest) -> BotSnapshot:
        snapshot = request.snapshot
        return BotSnapshot(
            board=snapshot.board.copy(),
            active=snapshot.active.piece,
            queue=list(snapshot.queue),
            hold=snapshot.hold,
            combo=self.derived_state.combo,
            back_to_back=self.derived_state.back_to_back,
            piece_stream=self.piece_stream.snapshot(),
            incoming_garbage=(
                None
                if request.incoming_garbage is None
                else list(request.incoming_garbage)
            ),
            extensions=(
                None if request.extensions is None else dict(request.extensions)
            ),
        )

    def _validate(self, snapshot: ObservedSnapshot, rules: Rules) -> Optional[str]:
        if snapshot.board.width != rules.board_width:
            return f"board must have {rules.board_width} columns"
        if snapshot.board.height != rules.board_height:
            return f"board must have {rules.board_height} rows"
        return None

    def _log_reconciliation(
        self,
        transition: SessionTransition,
        reconciliation: Reconciliation,
        incoming: ObservedSnapshot,
    ) -> None:
        reason = (
            transition.reconciliation_reason.value
            if transition.reconciliation_reason
            else "unknown"
        )
        print(
            "[info] reconciliation: "
            f"reason={reason} "
            f"seq={incoming.seq} "
            f"action={reconciliation.action.value} "
            f"piece_stream={transition.piece_stream_action.value}",
            file=sys.stderr,
        )

    def _schedule_go_idle(self) -> None:
        if self._idle_s <= 0:
            return
        self._go_idle_generation += 1
        generation = self._go_idle_generation
        timer = threading.Timer(self._idle_s, self._go_idle, [generation])
        timer.daemon = True
        self._go_idle_timer = timer
        timer.start()

    def _cancel_go_idle(self) -> None:
        self._go_idle_generation += 1
        if self._go_idle_timer is not None:
            self._go_idle_timer.cancel()
            self._go_idle_timer = None

    def _go_idle(self, generation: int) -> None:
        with self._lock:
            if generation != self._go_idle_generation:
                return
            self._go_idle_timer = None
            print("[info] minorail going idle; closing bot process", file=sys.stderr)
            self.bot_session.close()
            self._bot_game_active = False
            self._bot_needs_start = True
