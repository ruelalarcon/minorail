from __future__ import annotations

from typing import Protocol

from tetris.game.state import AppliedMove


class AttackCalculator(Protocol):
    """Produce positive attack chunks in cancellation and sending order."""

    def packets(self, applied: AppliedMove) -> tuple[int, ...]: ...
