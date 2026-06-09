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
    ) -> None:
        self._bot_path = bot_path
        self._settings = settings
        self._visualizer = visualizer
        self._session_id = session_id

        protocol_cfg = self._settings.get("protocol", {})
        protocol_start_cfg = protocol_cfg.get("start", {})
        service_path_cfg = self._settings.get("service", {}).get("path", {})
        self._convert_sonic_drops = service_path_cfg.get("convert_sonic_drops", False)
        logging_cfg = self._settings.get("logging", {})
        bot_info_cfg = logging_cfg.get("bot_info", {})
        self._service = SuggestionService(
            self._bot_path,
            piece_stream_limit=protocol_start_cfg.get("piece_stream_limit", 11),
            info_print_topics=bot_info_cfg.get("print", ["warning"]),
        )

        self._rules = Rules.from_settings(self._settings)
        rand = make_randomizer(self._rules.randomizer)
        assert rand is not None
        self._rand: Randomizer = rand
        active = spawn_location(self._rand.next())
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

        self._visualizer.on_game_started(self.state)

        try:
            while True:
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
                    break
                self.seq += 1
                if result.placement is None:
                    self._visualizer.error(
                        f"no suggestion: {result.reason or result.status.value}"
                    )
                    break

                chosen = result.placement
                hold_used = chosen.location.piece != spawn_piece

                moving_piece = moving_piece_for(self.snapshot(), chosen)
                if moving_piece is None:
                    self._visualizer.error(f"no valid move: {chosen}")
                    break

                self._visualizer.animate_suggestion(
                    self.state, moving_piece, result, hold_used, self._rules
                )

                ok = self.state.apply_move(chosen, self._rules)
                if not ok:
                    self._visualizer.error(f"apply_move rejected: {chosen}")
                    break

                self.last_move = chosen
                self._ensure_queue_refilled(self.state, self._rand, refill_at)

                pieces_placed += 1
                self._visualizer.on_piece_locked(self.state)

                if any(self.state.board.cols[x] >> 20 != 0 for x in range(10)):
                    self._visualizer.on_top_out(self.state)
                    self._visualizer.error("topped out")
                    break
        except KeyboardInterrupt:
            interrupted = True
            raise
        finally:
            elapsed = time.time() - start_time
            try:
                self.close()
            except KeyboardInterrupt:
                if not interrupted:
                    raise

        return {
            "pieces": pieces_placed,
            "elapsed": elapsed,
            "pps": pieces_placed / elapsed if elapsed > 0 else 0,
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
