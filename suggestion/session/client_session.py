from __future__ import annotations

import sys
import threading
from typing import Any, Callable, Optional, Protocol

from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.movegen.pathfinder import convert_sonic_drops, find_path
from suggestion.derived_state import DerivedState
from suggestion.move_selection import moving_piece_for, pick_move
from suggestion.piece_stream_tracker import PieceStreamTracker
from suggestion.session.transition import (
    BotAction,
    PieceStreamAction,
    SessionTransition,
    classify_transition,
    observed_pieces,
)
from suggestion.contracts.bot_snapshot import BotSnapshot
from suggestion.contracts.observed_snapshot import ObservedSnapshot
from suggestion.contracts.suggestion_request import SuggestionRequest
from suggestion.contracts.suggestion_result import SuggestionResult
from suggestion.contracts.suggestion_status import SuggestionStatus


class BotSessionLike(Protocol):
    def start_from(self, snapshot: BotSnapshot, rules: Rules) -> None: ...

    def suggest(
        self, timeout_ms: int, extensions: dict[str, Any] | None = None
    ) -> list[Placement]: ...

    def advance_with(
        self, placement: Placement, new_pieces: list[Piece] | None = None
    ) -> None: ...

    def reset_from(self, snapshot: BotSnapshot, rules: Rules) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


BotSessionFactory = Callable[[], BotSessionLike]


class ClientSession:
    def __init__(
        self,
        bot_session_factory: BotSessionFactory,
        piece_stream_limit: int = 11,
        idle_ms: int = 20_000,
    ) -> None:
        self._lock = threading.RLock()
        self._idle_s = idle_ms / 1000
        self._go_idle_timer: threading.Timer | None = None
        self._go_idle_generation = 0
        self._bot_needs_start = False
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
            self.bot_session.stop()
            self.bot_session.close()

    def _suggest_locked(self, request: SuggestionRequest) -> SuggestionResult:
        validation_error = self._validate(request.snapshot)
        if validation_error is not None:
            return SuggestionResult(
                seq=request.snapshot.seq,
                status=SuggestionStatus.Invalid,
                placements=[],
                placement=None,
                path=None,
                reason=validation_error,
            )

        transition = self._sync_to_request(request)
        self._apply_bot_action(transition, request)

        moves = self.bot_session.suggest(request.timeout_ms, request.extensions)
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
        if request.include_path:
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
            status=transition.status,
            placements=moves,
            placement=chosen,
            path=path,
            reason=reason,
        )

    def _sync_to_request(self, request: SuggestionRequest) -> SessionTransition:
        incoming = request.snapshot
        self.rules = request.rules
        transition = classify_transition(
            shadow_observed=self.shadow_observed,
            incoming=incoming,
            previous_suggestion=self.previous_suggestion,
            derived_state=self.derived_state,
            rules=request.rules,
        )

        if transition.status == SuggestionStatus.Advanced:
            assert transition.expected is not None
            self.derived_state.update_from_confirmed(transition.expected.state)
        elif transition.status == SuggestionStatus.Resynced:
            self._log_resync(transition, incoming)
            self.derived_state.repair_or_reset(incoming, request.rules)
        elif transition.bot_action == BotAction.Start:
            self.derived_state = DerivedState.from_observed(incoming)

        self._apply_piece_stream_action(transition, incoming)
        return transition

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
            case PieceStreamAction.Resync:
                self.piece_stream.resync(observed_pieces(incoming))

    def _apply_bot_action(
        self, transition: SessionTransition, request: SuggestionRequest
    ) -> None:
        bot_snapshot = self._to_bot_snapshot(request.snapshot, request.extensions)
        if self._bot_needs_start:
            self.bot_session.start_from(bot_snapshot, request.rules)
            self._bot_needs_start = False
            return

        match transition.bot_action:
            case BotAction.Start:
                self.bot_session.start_from(bot_snapshot, request.rules)
            case BotAction.Keep:
                pass
            case BotAction.Advance:
                assert self.previous_suggestion is not None
                assert transition.expected is not None
                self.bot_session.advance_with(
                    self.previous_suggestion, transition.expected.new_pieces
                )
            case BotAction.Reset:
                self.bot_session.reset_from(bot_snapshot, request.rules)

    def _to_bot_snapshot(
        self, snapshot: ObservedSnapshot, extensions: dict[str, Any] | None = None
    ) -> BotSnapshot:
        return BotSnapshot(
            board=snapshot.board.copy(),
            active=snapshot.active.piece,
            queue=list(snapshot.queue),
            hold=snapshot.hold,
            combo=self.derived_state.combo,
            back_to_back=self.derived_state.back_to_back,
            piece_stream=self.piece_stream.snapshot(),
            extensions=None if extensions is None else dict(extensions),
        )

    def _validate(self, snapshot: ObservedSnapshot) -> Optional[str]:
        if len(snapshot.board.cols) != 10:
            return "board must have 10 columns"
        return None

    def _log_resync(
        self, transition: SessionTransition, incoming: ObservedSnapshot
    ) -> None:
        resync_type = (
            transition.resync_type.value if transition.resync_type else "unknown"
        )
        print(
            "[info] minorail resync: "
            f"type={resync_type} "
            f"seq={incoming.seq} "
            f"bot_action={transition.bot_action.value} "
            f"piece_stream_action={transition.piece_stream_action.value}",
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
            self._bot_needs_start = True
