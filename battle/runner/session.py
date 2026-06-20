from __future__ import annotations

import sys
import time
from typing import Any

from battle.attack import ATTACK_CALCULATORS
from battle.attack.base import AttackCalculator
from battle.garbage import GARBAGE_RULES
from battle.garbage.base import GarbageRules
from battle.runner.events import (
    GameEndedEvent,
    GameStartedEvent,
    GarbageAppliedEvent,
    PieceLockedEvent,
    RunObserver,
)
from battle.runner.player import Player
from battle.runner.visualizer import BattleVisualizer
from bots.session import BotStartupError
from settings import PathSettings, RunLimits, Settings
from solo.runner.metrics import occupied_cells, stack_height
from solo.runner.session import SuggestionServiceLike
from suggestion.move_selection import moving_piece_for
from suggestion.service import SuggestionService
from tetris.model.rules import Rules


class Session:
    def __init__(
        self,
        bot_a_path: str,
        bot_b_path: str,
        *,
        settings: Settings,
        visualizer: BattleVisualizer,
        session_id: str = "battle",
        bot_a_args: list[str] | None = None,
        bot_b_args: list[str] | None = None,
        service_a: SuggestionServiceLike | None = None,
        service_b: SuggestionServiceLike | None = None,
        suggestion_session_id_a: str | None = None,
        suggestion_session_id_b: str | None = None,
        random_seed: int | None = None,
        limits: RunLimits | None = None,
        pathfinding: PathSettings | None = None,
        observers: list[RunObserver] | None = None,
    ) -> None:
        self._settings = settings
        self._visualizer = visualizer
        self._session_id = session_id
        self._random_seed = random_seed
        self._limits = limits or settings.run_limits()
        self._pathfinding = pathfinding or PathSettings(pathfinding=True)
        self._observers = observers or []
        self._rules = Rules.from_values(settings.rules_values())
        self._owns_a = service_a is None
        self._owns_b = service_b is None

        protocol_start = settings.protocol_start()
        bot_cfg = settings.bot()
        self._service_a = service_a or SuggestionService(
            bot_a_path,
            bot_args=bot_a_args or [],
            piece_stream_limit=protocol_start.piece_stream_limit,
            info_print_topics=settings.bot_info_topics(),
            idle_ms=bot_cfg.idle_ms,
        )
        self._service_b = service_b or SuggestionService(
            bot_b_path,
            bot_args=bot_b_args or [],
            piece_stream_limit=protocol_start.piece_stream_limit,
            info_print_topics=settings.bot_info_topics(),
            idle_ms=bot_cfg.idle_ms,
        )

        self._players = [
            Player.start(
                name="A",
                settings=settings,
                rules=self._rules,
                seed=settings.base_seed(random_seed),
                service=self._service_a,
                suggestion_session_id=suggestion_session_id_a or f"{session_id}:A",
            ),
            Player.start(
                name="B",
                settings=settings,
                rules=self._rules,
                seed=settings.base_seed(random_seed),
                service=self._service_b,
                suggestion_session_id=suggestion_session_id_b or f"{session_id}:B",
            ),
        ]

        attack_name = settings.battle_attack().calculator
        garbage_name = settings.battle_garbage().rules
        try:
            self._attack: AttackCalculator = ATTACK_CALCULATORS[attack_name]()
        except KeyError as e:
            raise ValueError(f"unknown battle.attack.calculator: {attack_name}") from e
        try:
            garbage_type = GARBAGE_RULES[garbage_name]
        except KeyError as e:
            raise ValueError(f"unknown battle.garbage.rules: {garbage_name}") from e
        self._garbage: list[GarbageRules] = [
            garbage_type(seed=settings.base_seed(random_seed)),
            garbage_type(seed=None if random_seed is None else random_seed + 1),
        ]
        for player, garbage_rules in zip(self._players, self._garbage):
            player.garbage_queue = garbage_rules.empty_queue()

    def play_game(self) -> dict[str, Any]:
        bot_cfg = self._settings.bot()
        refill_at = self._settings.game_queue().refill_threshold
        start_time = time.time()
        status = "unknown"
        winner: str | None = None
        loser: str | None = None
        interrupted = False
        turn = 0

        self._visualizer.on_game_started(self._states(), self._incoming())
        self._notify_game_started()

        try:
            while True:
                if self._time_limit_reached(start_time):
                    status = "time_limit"
                    break

                player_index = turn % 2
                player = self._players[player_index]
                opponent = self._players[1 - player_index]
                garbage_rules = self._garbage[player_index]
                player.game.refill_queue(refill_at)
                spawn_piece = player.game.state.active.piece
                self._visualizer.on_spawn(
                    player.name, self._states(), self._incoming(), spawn_piece
                )

                try:
                    result = player.suggest(
                        rules=self._rules,
                        pathfinding=self._pathfinding,
                        timeout_ms=bot_cfg.suggest_timeout_ms,
                    )
                except BotStartupError as e:
                    print(
                        f"[error] bot startup failed for player {player.name}: {e}",
                        file=sys.stderr,
                    )
                    status = "bot_startup_failed"
                    loser = player.name
                    winner = opponent.name
                    break

                player.game.advance_seq()
                if result.placement is None:
                    self._visualizer.error(
                        f"{player.name} no suggestion: {result.reason or result.status.value}"
                    )
                    status = "no_suggestion"
                    loser = player.name
                    winner = opponent.name
                    break

                chosen = result.placement
                hold_used = chosen.location.piece != spawn_piece
                moving_piece = moving_piece_for(player.snapshot(), chosen)
                if moving_piece is None:
                    self._visualizer.error(f"{player.name} no valid move: {chosen}")
                    status = "invalid_move"
                    loser = player.name
                    winner = opponent.name
                    break

                self._visualizer.animate_suggestion(
                    player.name,
                    self._states(),
                    self._incoming(),
                    moving_piece,
                    result,
                    hold_used,
                    self._rules,
                )

                applied = player.game.apply_placement(chosen)
                if applied is None:
                    self._visualizer.error(
                        f"{player.name} apply_move rejected: {chosen}"
                    )
                    status = "apply_move_rejected"
                    loser = player.name
                    winner = opponent.name
                    break

                incoming_before = garbage_rules.queue_total(player.garbage_queue)
                attack = self._attack.calculate(applied)
                exchange = garbage_rules.exchange(
                    attack=attack.attack,
                    queue=player.garbage_queue,
                )
                player.garbage_queue = exchange.queue_after
                opponent_garbage_rules = self._garbage[1 - player_index]
                opponent.garbage_queue = opponent_garbage_rules.enqueue_attack(
                    opponent.garbage_queue,
                    attack=exchange.sent,
                )

                garbage_applied = None
                if garbage_rules.should_apply_on_lock(
                    lines_cleared=applied.lines_cleared
                ):
                    garbage_applied = garbage_rules.apply_queue(
                        player.game.state,
                        player.garbage_queue,
                    )
                    player.garbage_queue = garbage_applied.queue_after

                player.game.refill_queue(refill_at)
                self._notify_piece_locked(
                    PieceLockedEvent(
                        session_id=self._session_id,
                        player=player.name,
                        piece_index=player.pieces_locked,
                        placement=chosen,
                        hold_used=hold_used,
                        applied=applied,
                        stack_height=stack_height(player.game.state),
                        occupied_cells=occupied_cells(player.game.state),
                        attack=attack.attack,
                        attack_breakdown=attack.breakdown,
                        incoming_garbage_before=incoming_before,
                        garbage_cancelled=exchange.cancelled,
                        garbage_sent=exchange.sent,
                        incoming_garbage_after=garbage_rules.queue_total(
                            player.garbage_queue
                        ),
                    )
                )
                player.pieces_locked += 1
                self._visualizer.on_piece_locked(
                    player.name, self._states(), self._incoming()
                )

                if garbage_applied is not None and garbage_applied.lines > 0:
                    event = GarbageAppliedEvent(
                        session_id=self._session_id,
                        player=player.name,
                        lines=garbage_applied.lines,
                        incoming_garbage_after=garbage_rules.queue_total(
                            player.garbage_queue
                        ),
                        stack_height=stack_height(player.game.state),
                        occupied_cells=occupied_cells(player.game.state),
                    )
                    self._notify_garbage_applied(event)
                    self._visualizer.on_garbage_applied(
                        player.name,
                        garbage_applied.lines,
                        self._states(),
                        self._incoming(),
                    )

                if player.game.is_topped_out() or (
                    garbage_applied is not None and garbage_applied.topped_out
                ):
                    status = "topout"
                    loser = player.name
                    winner = opponent.name
                    break

                if self._limits.piece_limit is not None:
                    if (
                        sum(p.pieces_locked for p in self._players)
                        >= self._limits.piece_limit
                    ):
                        status = "piece_limit"
                        break

                turn += 1
        except KeyboardInterrupt:
            interrupted = True
            status = "interrupted"
            raise
        finally:
            elapsed = time.time() - start_time
            try:
                for player in self._players:
                    player.service.stop_game(player.suggestion_session_id)
                if self._owns_a:
                    self._service_a.close()
                if self._owns_b:
                    self._service_b.close()
            except KeyboardInterrupt:
                if not interrupted:
                    raise
            self._visualizer.on_game_ended(
                self._states(), self._incoming(), status, winner, loser
            )
            self._notify_game_ended(status, winner, loser, elapsed)

        pieces = {p.name: p.pieces_locked for p in self._players}
        total = sum(pieces.values())
        return {
            "status": status,
            "winner": winner,
            "loser": loser,
            "pieces": pieces,
            "total_pieces": total,
            "elapsed": elapsed,
            "pps": total / elapsed if elapsed > 0 else 0,
        }

    def _states(self) -> dict[str, Any]:
        return {p.name: p.game.state for p in self._players}

    def _incoming(self) -> dict[str, int]:
        return {
            player.name: garbage_rules.queue_total(player.garbage_queue)
            for player, garbage_rules in zip(self._players, self._garbage)
        }

    def _notify_game_started(self) -> None:
        event = GameStartedEvent(
            session_id=self._session_id,
            seed=self._random_seed,
            players=(self._players[0].name, self._players[1].name),
        )
        for observer in self._observers:
            observer.on_game_started(event)

    def _notify_piece_locked(self, event: PieceLockedEvent) -> None:
        for observer in self._observers:
            observer.on_piece_locked(event)

    def _notify_garbage_applied(self, event: GarbageAppliedEvent) -> None:
        for observer in self._observers:
            observer.on_garbage_applied(event)

    def _notify_game_ended(
        self,
        status: str,
        winner: str | None,
        loser: str | None,
        elapsed: float,
    ) -> None:
        pieces = {p.name: p.pieces_locked for p in self._players}
        total = sum(pieces.values())
        event = GameEndedEvent(
            session_id=self._session_id,
            status=status,
            winner=winner,
            loser=loser,
            pieces=pieces,
            elapsed=elapsed,
            pps=total / elapsed if elapsed > 0 else 0,
            stack_height={p.name: stack_height(p.game.state) for p in self._players},
            occupied_cells={
                p.name: occupied_cells(p.game.state) for p in self._players
            },
            incoming_garbage=self._incoming(),
        )
        for observer in self._observers:
            observer.on_game_ended(event)

    def _time_limit_reached(self, start_time: float) -> bool:
        if self._limits.time_limit_ms is None:
            return False
        return (time.time() - start_time) * 1000 >= self._limits.time_limit_ms
