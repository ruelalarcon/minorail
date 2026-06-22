from __future__ import annotations

from typing import Any

from battle.runner.events import (
    GameEndedEvent,
    GameStartedEvent,
    GarbageAppliedEvent,
    PieceLockedEvent,
)
from solo.evaluation.collector import _placement


class EvaluationCollector:
    def __init__(self, *, include_events: bool = True) -> None:
        self.seed: int | None = None
        self.players: tuple[str, str] = ("A", "B")
        self.events: list[dict[str, Any]] = []
        self._include_events = include_events
        self._summary: dict[str, Any] = {
            "status": "unknown",
            "winner": None,
            "loser": None,
            "pieces": 0,
            "player_pieces": {"A": 0, "B": 0},
            "elapsed_ms": 0,
            "pps": 0.0,
            "lines_cleared": {"A": 0, "B": 0},
            "line_clear_placements": {"A": 0, "B": 0},
            "combo_steps": {"A": 0, "B": 0},
            "max_combo": {"A": 0, "B": 0},
            "back_to_back_steps": {"A": 0, "B": 0},
            "max_back_to_back": {"A": 0, "B": 0},
            "attack": {"A": 0, "B": 0},
            "max_attack": {"A": 0, "B": 0},
            "attack_placements": {"A": 0, "B": 0},
            "perfect_clears": {"A": 0, "B": 0},
            "holds": {"A": 0, "B": 0},
            "garbage_sent": {"A": 0, "B": 0},
            "garbage_cancelled": {"A": 0, "B": 0},
            "garbage_applied": {"A": 0, "B": 0},
            "max_incoming_garbage": {"A": 0, "B": 0},
        }

    def on_game_started(self, event: GameStartedEvent) -> None:
        self.seed = event.seed
        self.players = event.players
        self._append_event(
            {
                "type": "game_started",
                "seed": event.seed,
                "players": list(event.players),
            }
        )

    def on_piece_locked(self, event: PieceLockedEvent) -> None:
        player = event.player
        applied = event.applied
        self._summary["lines_cleared"][player] += applied.lines_cleared
        if applied.lines_cleared > 0:
            self._summary["line_clear_placements"][player] += 1
        if applied.combo_after > applied.combo_before:
            self._summary["combo_steps"][player] += 1
        self._summary["max_combo"][player] = max(
            self._summary["max_combo"][player],
            applied.combo_after,
        )
        if applied.back_to_back_after > applied.back_to_back_before:
            self._summary["back_to_back_steps"][player] += 1
        self._summary["max_back_to_back"][player] = max(
            self._summary["max_back_to_back"][player],
            applied.back_to_back_after,
        )
        if applied.perfect_clear:
            self._summary["perfect_clears"][player] += 1
        if event.hold_used:
            self._summary["holds"][player] += 1
        self._summary["attack"][player] += event.attack
        self._summary["max_attack"][player] = max(
            self._summary["max_attack"][player],
            event.attack,
        )
        if event.attack > 0:
            self._summary["attack_placements"][player] += 1
        self._summary["garbage_sent"][player] += event.garbage_sent
        self._summary["garbage_cancelled"][player] += event.garbage_cancelled
        self._summary["max_incoming_garbage"][player] = max(
            self._summary["max_incoming_garbage"][player],
            event.incoming_garbage_before,
            event.incoming_garbage_after,
        )
        self._append_event(
            {
                "type": "piece_locked",
                "player": player,
                "piece_index": event.piece_index,
                "placement": _placement(event.placement),
                "hold_used": event.hold_used,
                "lines_cleared": applied.lines_cleared,
                "perfect_clear": applied.perfect_clear,
                "combo_before": applied.combo_before,
                "combo_after": applied.combo_after,
                "back_to_back_before": applied.back_to_back_before,
                "back_to_back_after": applied.back_to_back_after,
                "stack_height": event.stack_height,
                "occupied_cells": event.occupied_cells,
                "attack": event.attack,
                "incoming_garbage_before": event.incoming_garbage_before,
                "garbage_cancelled": event.garbage_cancelled,
                "garbage_sent": event.garbage_sent,
                "incoming_garbage_after": event.incoming_garbage_after,
            }
        )

    def on_garbage_applied(self, event: GarbageAppliedEvent) -> None:
        self._summary["garbage_applied"][event.player] += event.lines
        self._summary["max_incoming_garbage"][event.player] = max(
            self._summary["max_incoming_garbage"][event.player],
            event.incoming_garbage_after,
        )
        self._append_event(
            {
                "type": "garbage_applied",
                "player": event.player,
                "lines": event.lines,
                "incoming_garbage_after": event.incoming_garbage_after,
                "stack_height": event.stack_height,
                "occupied_cells": event.occupied_cells,
            }
        )

    def on_game_ended(self, event: GameEndedEvent) -> None:
        total = sum(event.pieces.values())
        self._summary["status"] = event.status
        self._summary["winner"] = event.winner
        self._summary["loser"] = event.loser
        self._summary["pieces"] = total
        self._summary["player_pieces"] = dict(event.pieces)
        self._summary["elapsed_ms"] = round(event.elapsed * 1000)
        self._summary["pps"] = event.pps
        self._append_event(
            {
                "type": "game_ended",
                "status": event.status,
                "winner": event.winner,
                "loser": event.loser,
                "pieces": total,
                "player_pieces": dict(event.pieces),
                "elapsed_ms": round(event.elapsed * 1000),
                "pps": event.pps,
                "stack_height": dict(event.stack_height),
                "occupied_cells": dict(event.occupied_cells),
                "incoming_garbage": dict(event.incoming_garbage),
            }
        )

    def result(self, *, game: int) -> dict[str, Any]:
        result = {
            "game": game,
            "seed": self.seed,
            "players": list(self.players),
            "summary": self._copy_summary(),
        }
        if self._include_events:
            result["events"] = list(self.events)
        return result

    def _append_event(self, event: dict[str, Any]) -> None:
        if self._include_events:
            self.events.append(event)

    def _copy_summary(self) -> dict[str, Any]:
        copied = {}
        for key, value in self._summary.items():
            copied[key] = dict(value) if isinstance(value, dict) else value
        return copied
