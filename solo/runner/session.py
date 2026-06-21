from __future__ import annotations

import sys
import time
from typing import Any, Protocol

from settings import PathSettings, RunLimits, Settings
from bots.session import BotStartupError
from contracts.observed_snapshot import ObservedSnapshot
from contracts.suggestion_request import SuggestionRequest
from contracts.suggestion_result import SuggestionResult
from solo.runner.controls import GameControls
from solo.runner.events import (
    GameEndedEvent,
    GameStartedEvent,
    PieceLockedEvent,
    RunObserver,
)
from solo.runner.local_game import LocalGame
from solo.runner.metrics import occupied_cells, stack_height
from solo.runner.visualizer import SoloVisualizer
from suggestion.move_selection import moving_piece_for
from suggestion.service import SuggestionService
from tetris.attack.registry import AttackCalculator, attack_calculator
from tetris.game.state import GameState
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.randomizer import Randomizer, make_randomizer


class SuggestionServiceLike(Protocol):
    def suggest(self, request: SuggestionRequest) -> SuggestionResult: ...

    def stop_game(self, session_id: str) -> None: ...

    def close(self) -> None: ...


class LocalGameSession:
    def __init__(
        self,
        bot_path: str,
        settings: Settings,
        visualizer: SoloVisualizer,
        session_id: str = "terminal",
        suggestion_session_id: str | None = None,
        suggestion_service: SuggestionServiceLike | None = None,
        bot_args: list[str] | None = None,
        random_seed: int | None = None,
        limits: RunLimits | None = None,
        pathfinding: PathSettings | None = None,
        observers: list[RunObserver] | None = None,
    ) -> None:
        self._bot_path = bot_path
        self._bot_args = bot_args or []
        self._settings = settings
        self._visualizer = visualizer
        self._session_id = session_id
        self._suggestion_session_id = suggestion_session_id or session_id
        self._random_seed = random_seed
        self._limits = limits or self._settings.run_limits()
        self._pathfinding = pathfinding or PathSettings(pathfinding=True)
        self._observers = observers or []
        self._owns_service = suggestion_service is None

        protocol_start = self._settings.protocol_start()
        bot_cfg = self._settings.bot()
        self._service = suggestion_service or SuggestionService(
            self._bot_path,
            bot_args=self._bot_args,
            piece_stream_limit=protocol_start.piece_stream_limit,
            info_print_topics=self._settings.bot_info_topics(),
            idle_ms=bot_cfg.idle_ms,
        )

        self._rules = Rules.from_values(self._settings.rules_values())
        attack_name = settings.attack().calculator
        self._attack: AttackCalculator = attack_calculator(attack_name)()
        rand = make_randomizer(
            self._rules.randomizer,
            seed=self._settings.base_seed(random_seed),
        )
        assert rand is not None
        self._randomizer: Randomizer = rand
        queue_cfg = self._settings.game_queue()
        self._game = LocalGame.start(
            rules=self._rules,
            randomizer=self._randomizer,
            initial_pieces=queue_cfg.initial,
        )

        self._visualizer.set_game_controls(
            GameControls(
                set_cell=self.set_cell,
                clear_board=self.clear_board,
                get_state=lambda: self.state,
            )
        )

    @property
    def state(self) -> GameState:
        return self._game.state

    @property
    def seq(self) -> int:
        return self._game.seq

    @property
    def last_move(self) -> Placement | None:
        return self._game.last_move

    def close(self) -> None:
        self._service.close()

    def set_cell(self, x: int, y: int, filled: bool) -> None:
        self._game.set_cell(x, y, filled)

    def clear_board(self) -> None:
        self._game.clear_board()

    def snapshot(self) -> ObservedSnapshot:
        return self._game.snapshot()

    def play_game(self) -> dict[str, Any]:
        bot_cfg = self._settings.bot()
        refill_at = self._settings.game_queue().refill_threshold

        pieces_placed = 0
        total_attack = 0
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

                self._game.refill_queue(refill_at)
                spawn_piece = self.state.active.piece
                self._visualizer.on_spawn(self.state, spawn_piece)

                try:
                    result = self._service.suggest(
                        SuggestionRequest(
                            snapshot=self.snapshot(),
                            rules=self._rules,
                            pathfinding=self._pathfinding.pathfinding,
                            convert_sonic_drops=(self._pathfinding.convert_sonic_drops),
                            session_id=self._suggestion_session_id,
                            timeout_ms=bot_cfg.suggest_timeout_ms,
                        )
                    )
                except BotStartupError as e:
                    print(f"[error] bot startup failed: {e}", file=sys.stderr)
                    status = "bot_startup_failed"
                    break

                self._game.advance_seq()
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
                    self.state,
                    moving_piece,
                    result,
                    hold_used,
                    self._rules,
                )

                applied = self._game.apply_placement(chosen)
                if applied is None:
                    self._visualizer.error(f"apply_move rejected: {chosen}")
                    status = "apply_move_rejected"
                    break

                attack = self._attack.calculate(applied)
                total_attack += attack
                self._game.refill_queue(refill_at)
                self._notify_piece_locked(
                    PieceLockedEvent(
                        session_id=self._session_id,
                        piece_index=pieces_placed,
                        placement=chosen,
                        hold_used=hold_used,
                        applied=applied,
                        stack_height=stack_height(self.state),
                        occupied_cells=occupied_cells(self.state),
                        attack=attack,
                    )
                )
                pieces_placed += 1
                self._visualizer.on_piece_locked(
                    self.state,
                    total_attack=total_attack,
                )

                if self._game.is_topped_out():
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
                self._service.stop_game(self._suggestion_session_id)
                if self._owns_service:
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
                    stack_height=stack_height(self.state),
                    occupied_cells=occupied_cells(self.state),
                )
            )

        return {
            "pieces": pieces_placed,
            "elapsed": elapsed,
            "pps": pieces_placed / elapsed if elapsed > 0 else 0,
            "status": status,
        }

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
