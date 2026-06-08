from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from core.piece import Piece
from core.placement import Placement
from game.rules import Rules
from game.state import GameState
from movegen.pathfinder import find_path
from service.derived_state import DerivedState
from service.move_selection import moving_piece_for, pick_move
from service.piece_stream import PieceStreamTracker
from service.snapshot import (
    BotSnapshot,
    ObservedSnapshot,
    SuggestionRequest,
    SuggestionResult,
    SuggestionStatus,
)


class BotSessionLike(Protocol):
    def start_from(self, snapshot: BotSnapshot, rules: Rules) -> None: ...

    def suggest(self, timeout_ms: int) -> list[Placement]: ...

    def advance_with(
        self, placement: Placement, new_pieces: list[Piece] | None = None
    ) -> None: ...

    def reset_from(self, snapshot: BotSnapshot, rules: Rules) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


BotSessionFactory = Callable[[], BotSessionLike]


@dataclass
class _ExpectedAdvance:
    snapshot: ObservedSnapshot
    state: GameState
    new_pieces: list[Piece]


class ClientSession:
    def __init__(
        self, bot_session_factory: BotSessionFactory, piece_stream_limit: int = 11
    ) -> None:
        self.latest_observed: Optional[ObservedSnapshot] = None
        self.shadow_observed: Optional[ObservedSnapshot] = None
        self.derived_state = DerivedState.neutral()
        self.piece_stream = PieceStreamTracker(piece_stream_limit)
        self.previous_suggestion: Optional[Placement] = None
        self.bot_session: BotSessionLike = bot_session_factory()
        self.rules: Optional[Rules] = None

    def suggest(self, request: SuggestionRequest) -> SuggestionResult:
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

        status = self._sync_to_request(request)
        bot_snapshot = self._to_bot_snapshot(request.snapshot)
        if status == SuggestionStatus.Resynced:
            self.bot_session.reset_from(bot_snapshot, request.rules)
        elif self.shadow_observed is None:
            self.bot_session.start_from(bot_snapshot, request.rules)

        moves = self.bot_session.suggest(request.timeout_ms)
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
            if path is None:
                reason = "no path found for selected placement"

        self.latest_observed = request.snapshot.copy()
        self.shadow_observed = request.snapshot.copy()
        self.previous_suggestion = chosen
        self.rules = request.rules
        return SuggestionResult(
            seq=request.snapshot.seq,
            status=status,
            placements=moves,
            placement=chosen,
            path=path,
            reason=reason,
        )

    def close(self) -> None:
        self.bot_session.stop()
        self.bot_session.close()

    def _sync_to_request(self, request: SuggestionRequest) -> SuggestionStatus:
        incoming = request.snapshot
        self.rules = request.rules

        if self.shadow_observed is None:
            self.derived_state = DerivedState.from_observed(incoming)
            self.piece_stream.initialize(incoming.queue)
            return SuggestionStatus.Synced

        if incoming.physically_equals(self.shadow_observed):
            return SuggestionStatus.Synced

        expected = self._expected_advance(incoming, request.rules)
        if expected is not None:
            self.derived_state.update_from_confirmed(expected.state)
            self.piece_stream.append(expected.new_pieces)
            if self.previous_suggestion is not None:
                self.bot_session.advance_with(
                    self.previous_suggestion, expected.new_pieces
                )
            return SuggestionStatus.Advanced

        self.derived_state.repair_or_reset(incoming, request.rules)
        self.piece_stream.resync(incoming.queue)
        return SuggestionStatus.Resynced

    def _expected_advance(
        self, incoming: ObservedSnapshot, rules: Rules
    ) -> Optional[_ExpectedAdvance]:
        if self.shadow_observed is None or self.previous_suggestion is None:
            return None

        state = self.derived_state.to_game_state(self.shadow_observed)
        if not state.apply_move(self.previous_suggestion, rules):
            return None

        expected_queue = list(state.queue)
        if not _is_prefix(expected_queue, incoming.queue):
            return None
        new_pieces = incoming.queue[len(expected_queue) :]
        state.queue.extend(new_pieces)

        expected = ObservedSnapshot(
            board=state.board.copy(),
            current=state.current_piece(),
            queue=list(state.queue),
            hold=state.hold,
            can_hold=True,
            seq=incoming.seq,
            last_move=self.previous_suggestion,
        )
        if not incoming.physically_equals(expected):
            return None
        return _ExpectedAdvance(snapshot=expected, state=state, new_pieces=new_pieces)

    def _to_bot_snapshot(self, snapshot: ObservedSnapshot) -> BotSnapshot:
        return BotSnapshot(
            board=snapshot.board.copy(),
            queue=list(snapshot.queue),
            hold=snapshot.hold,
            combo=self.derived_state.combo,
            back_to_back=self.derived_state.back_to_back,
            piece_stream=self.piece_stream.snapshot(),
        )

    def _validate(self, snapshot: ObservedSnapshot) -> Optional[str]:
        if len(snapshot.board.cols) != 10:
            return "board must have 10 columns"
        if snapshot.current is None:
            return "snapshot must include a current piece"
        if not snapshot.queue:
            return "queue must include the current piece"
        if snapshot.queue[0] != snapshot.current:
            return "current must match queue[0]"
        return None


def _is_prefix(prefix: list[Piece], values: list[Piece]) -> bool:
    return len(values) >= len(prefix) and values[: len(prefix)] == prefix
