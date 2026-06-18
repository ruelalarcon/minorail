from __future__ import annotations

import sys
import time
from typing import Any, Optional, Protocol

from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from runner.visualizer_protocol import CellEdit, EngineControls
from runner.events import EngineEvent, EngineEventType
from tetris.randomizer import Randomizer, make_randomizer
from tetris.model.rules import Rules
from tetris.game.state import GameState, spawn_location
from runner.observers import (
    EngineObserver,
    GameEndedEvent,
    GameStartedEvent,
    PieceLockedEvent,
)
from runner.limits import EngineLimits, engine_limits
from runner.seeding import base_seed
from suggestion.bot_session import BotStartupError
from suggestion.move_selection import moving_piece_for
from suggestion.contracts.observed_snapshot import ObservedSnapshot
from suggestion.contracts.suggestion_request import SuggestionRequest
from suggestion.contracts.suggestion_result import SuggestionResult
from suggestion.suggestion_service import SuggestionService


class Visualizer(Protocol):
    def on_game_started(self, state: GameState) -> None: ...

    def on_spawn(self, state: GameState, piece: Piece) -> None: ...

    def animate_suggestion(
        self,
        state: GameState,
        moving_piece: Piece,
        result: SuggestionResult,
        hold_used: bool,
        rules: Rules,
    ) -> None: ...

    def on_piece_locked(self, state: GameState) -> None: ...

    def on_top_out(self, state: GameState) -> None: ...

    def warning(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...

    def set_engine_controls(self, controls: EngineControls) -> None: ...


class EngineSession:
    def __init__(
        self,
        bot_path: str,
        settings: dict[str, Any],
        visualizer: Visualizer,
        session_id: str = "terminal",
        bot_args: list[str] | None = None,
        random_seed: int | None = None,
        limits: EngineLimits | None = None,
        observers: list[EngineObserver] | None = None,
    ) -> None:
        self._bot_path = bot_path
        self._bot_args = bot_args or []
        self._settings = settings
        self._visualizer = visualizer
        self._session_id = session_id
        self._random_seed = random_seed
        self._limits = limits or engine_limits(self._settings)
        self._observers = observers or []

        protocol_cfg = self._settings.get("protocol", {})
        protocol_start_cfg = protocol_cfg.get("start", {})
        service_path_cfg = self._settings.get("service", {}).get("path", {})
        self._convert_sonic_drops = service_path_cfg.get("convert_sonic_drops", False)
        logging_cfg = self._settings.get("logging", {})
        bot_info_cfg = logging_cfg.get("bot_info", {})
        bot_cfg = self._settings.get("bot", {})
        self._service = SuggestionService(
            self._bot_path,
            bot_args=self._bot_args,
            piece_stream_limit=protocol_start_cfg.get("piece_stream_limit", 11),
            info_print_topics=bot_info_cfg.get("print", ["warning"]),
            idle_ms=bot_cfg.get("idle_ms", 60_000),
        )

        self._rules = Rules.from_settings(self._settings)
        rand = make_randomizer(
            self._rules.randomizer,
            seed=base_seed(self._settings, random_seed),
        )
        assert rand is not None
        self._rand: Randomizer = rand
        active = spawn_location(
            self._rand.next(), x=self._rules.spawn_x, y=self._rules.spawn_y
        )
        self.state = GameState(
            board=Board(),
            active=active,
            queue=[
                self._rand.next()
                for _ in range(max(0, self._settings["engine"]["queue"]["initial"] - 1))
            ],
            hold=None,
            combo=0,
            back_to_back=0,
        )
        self.seq = 0
        self.last_move: Optional[Placement] = None

        self._visualizer.set_engine_controls(
            EngineControls(
                set_cell=self.set_cell,
                clear_board=self.clear_board,
                get_state=lambda: self.state,
            )
        )

    def close(self) -> None:
        self._service.close()

    def set_cell(self, x: int, y: int, filled: bool) -> list[EngineEvent]:
        return self.set_cells([CellEdit(x, y, filled)])

    def set_cells(self, edits: list[CellEdit]) -> list[EngineEvent]:
        changed: list[CellEdit] = []
        for edit in edits:
            self._validate_cell(edit.x, edit.y)
            mask = 1 << edit.y
            was_filled = bool(self.state.board.cols[edit.x] & mask)
            if was_filled == edit.filled:
                continue
            if edit.filled:
                self.state.board.cols[edit.x] |= mask
            else:
                self.state.board.cols[edit.x] &= ~mask
            changed.append(edit)

        if not changed:
            return []

        self.seq += 1
        self.last_move = None
        return [
            EngineEvent(
                EngineEventType.CellsChanged,
                self.seq,
                {"cells": changed},
            ),
            EngineEvent(
                EngineEventType.SnapshotChanged,
                self.seq,
                {"snapshot": self.snapshot()},
            ),
        ]

    def clear_board(self) -> list[EngineEvent]:
        edits = [
            CellEdit(x, y, False)
            for x in range(10)
            for y in range(40)
            if self.state.board.cols[x] & (1 << y)
        ]
        return self.set_cells(edits)

    def snapshot(self) -> ObservedSnapshot:
        return ObservedSnapshot(
            board=self.state.board.copy(),
            active=self.state.active,
            queue=list(self.state.queue),
            hold=self.state.hold,
            can_hold=not self.state.hold_used_this_turn,
            seq=self.seq,
            last_move=self.last_move,
        )

    def play_game(self) -> dict[str, Any]:
        cfg_b = self._settings["bot"]
        refill_at = self._settings["engine"]["queue"]["refill_threshold"]

        pieces_placed = 0
        start_time = time.time()
        interrupted = False
        status = "unknown"

        self._visualizer.on_game_started(self.state)
        self._notify_game_started()

        try:
            while True:
                if self._time_limit_reached(start_time):
                    status = "time_limit"
                    break

                self._ensure_queue_refilled(self.state, self._rand, refill_at)

                spawn_piece = self.state.active.piece

                self._visualizer.on_spawn(self.state, spawn_piece)

                try:
                    result = self._service.suggest(
                        SuggestionRequest(
                            snapshot=self.snapshot(),
                            rules=self._rules,
                            include_path=True,
                            convert_sonic_drops=self._convert_sonic_drops,
                            session_id=self._session_id,
                            timeout_ms=cfg_b["suggest_timeout_ms"],
                        )
                    )
                except BotStartupError as e:
                    print(f"[error] bot startup failed: {e}", file=sys.stderr)
                    status = "bot_startup_failed"
                    break
                self.seq += 1
                if result.placement is None:
                    self._visualizer.error(
                        f"no suggestion: {result.reason or result.status.value}"
                    )
                    status = "no_suggestion"
                    break

                chosen = result.placement
                hold_used = chosen.location.piece != spawn_piece

                moving_piece = moving_piece_for(self.snapshot(), chosen)
                if moving_piece is None:
                    self._visualizer.error(f"no valid move: {chosen}")
                    status = "invalid_move"
                    break

                self._visualizer.animate_suggestion(
                    self.state, moving_piece, result, hold_used, self._rules
                )

                applied = self.state.apply_move(chosen, self._rules)
                if applied is None:
                    self._visualizer.error(f"apply_move rejected: {chosen}")
                    status = "apply_move_rejected"
                    break

                self.last_move = chosen
                self._ensure_queue_refilled(self.state, self._rand, refill_at)

                self._notify_piece_locked(
                    PieceLockedEvent(
                        session_id=self._session_id,
                        piece_index=pieces_placed,
                        placement=chosen,
                        hold_used=hold_used,
                        applied=applied,
                        stack_height=_stack_height(self.state),
                        occupied_cells=_occupied_cells(self.state),
                    )
                )
                pieces_placed += 1
                self._visualizer.on_piece_locked(self.state)

                if any(self.state.board.cols[x] >> 20 != 0 for x in range(10)):
                    self._visualizer.on_top_out(self.state)
                    self._visualizer.error("topped out")
                    status = "topout"
                    break

                if self._limits.piece_limit is not None:
                    if pieces_placed >= self._limits.piece_limit:
                        status = "piece_limit"
                        break

                if self._time_limit_reached(start_time):
                    status = "time_limit"
                    break
        except KeyboardInterrupt:
            interrupted = True
            status = "interrupted"
            raise
        finally:
            elapsed = time.time() - start_time
            try:
                self.close()
            except KeyboardInterrupt:
                if not interrupted:
                    raise
            self._notify_game_ended(
                GameEndedEvent(
                    session_id=self._session_id,
                    status=status,
                    pieces=pieces_placed,
                    elapsed=elapsed,
                    pps=pieces_placed / elapsed if elapsed > 0 else 0,
                    stack_height=_stack_height(self.state),
                    occupied_cells=_occupied_cells(self.state),
                )
            )

        return {
            "pieces": pieces_placed,
            "elapsed": elapsed,
            "pps": pieces_placed / elapsed if elapsed > 0 else 0,
            "status": status,
        }

    def _ensure_queue_refilled(
        self,
        state: GameState,
        rand: Randomizer,
        refill_at: int,
    ) -> None:
        while len(state.queue) < refill_at:
            state.queue.append(rand.next())

    def _validate_cell(self, x: int, y: int) -> None:
        if x < 0 or x >= 10 or y < 0 or y >= 40:
            raise ValueError(f"cell out of bounds: ({x}, {y})")

    def _notify_game_started(self) -> None:
        event = GameStartedEvent(session_id=self._session_id, seed=self._random_seed)
        for observer in self._observers:
            observer.on_game_started(event)

    def _notify_piece_locked(self, event: PieceLockedEvent) -> None:
        for observer in self._observers:
            observer.on_piece_locked(event)

    def _notify_game_ended(self, event: GameEndedEvent) -> None:
        for observer in self._observers:
            observer.on_game_ended(event)

    def _time_limit_reached(self, start_time: float) -> bool:
        if self._limits.time_limit_ms is None:
            return False
        return (time.time() - start_time) * 1000 >= self._limits.time_limit_ms


def _stack_height(state: GameState) -> int:
    return max((col.bit_length() for col in state.board.cols), default=0)


def _occupied_cells(state: GameState) -> int:
    return sum(col.bit_count() for col in state.board.cols)
