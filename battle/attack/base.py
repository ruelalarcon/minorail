from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tetris.game.state import AppliedMove


@dataclass(frozen=True)
class AttackResult:
    attack: int
    breakdown: dict[str, int]


class AttackCalculator(Protocol):
    def calculate(self, applied: AppliedMove) -> AttackResult: ...
