from __future__ import annotations

from typing import Any

from solo.runner.events import GameEndedEvent, GameStartedEvent, PieceLockedEvent
from tetris.model.placement import Placement


class EvaluationCollector:
    def __init__(self, *, include_events: bool = True) -> None:
        self.seed: int | None = None
        self.events: list[dict[str, Any]] = []
        self._include_events = include_events
        self._summary = {
            "status": "unknown",
            "pieces": 0,
            "elapsed_ms": 0,
            "pps": 0.0,
            "lines_cleared": 0,
            "line_clear_placements": 0,
            "combo_steps": 0,
            "max_combo": 0,
            "back_to_back_steps": 0,
            "max_back_to_back": 0,
            "perfect_clears": 0,
            "holds": 0,
        }

    def on_game_started(self, event: GameStartedEvent) -> None:
        self.seed = event.seed

    def on_piece_locked(self, event: PieceLockedEvent) -> None:
        applied = event.applied
        combo_after = applied.combo_after
        back_to_back_after = applied.back_to_back_after

        self._summary["lines_cleared"] += applied.lines_cleared
        if applied.lines_cleared > 0:
            self._summary["line_clear_placements"] += 1
        if applied.combo_after > applied.combo_before:
            self._summary["combo_steps"] += 1
        self._summary["max_combo"] = max(self._summary["max_combo"], combo_after)
        if applied.back_to_back_after > applied.back_to_back_before:
            self._summary["back_to_back_steps"] += 1
        self._summary["max_back_to_back"] = max(
            self._summary["max_back_to_back"],
            back_to_back_after,
        )
        if applied.perfect_clear:
            self._summary["perfect_clears"] += 1
        if event.hold_used:
            self._summary["holds"] += 1

        self._append_event(
            {
                "type": "piece_locked",
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
            }
        )

    def on_game_ended(self, event: GameEndedEvent) -> None:
        self._summary["status"] = event.status
        self._summary["pieces"] = event.pieces
        self._summary["elapsed_ms"] = round(event.elapsed * 1000)
        self._summary["pps"] = event.pps
        self._append_event(
            {
                "type": "game_ended",
                "status": event.status,
                "pieces": event.pieces,
                "elapsed_ms": round(event.elapsed * 1000),
                "pps": event.pps,
                "stack_height": event.stack_height,
                "occupied_cells": event.occupied_cells,
            }
        )

    def result(self, *, game: int) -> dict[str, Any]:
        result = {
            "game": game,
            "seed": self.seed,
            "summary": dict(self._summary),
        }
        if self._include_events:
            result["events"] = list(self.events)
        return result

    def _append_event(self, event: dict[str, Any]) -> None:
        if self._include_events:
            self.events.append(event)


def _placement(placement: Placement) -> dict[str, Any]:
    loc = placement.location
    return {
        "piece": loc.piece.value,
        "orientation": loc.rotation.value,
        "x": loc.x,
        "y": loc.y,
        "spin": placement.spin.value,
    }
