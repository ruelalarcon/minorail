from __future__ import annotations

from typing import Protocol

from tetris.attack.classic_guideline import ClassicGuidelineAttackCalculator
from tetris.attack.modern_guideline import ModernGuidelineAttackCalculator
from tetris.attack.ppt import PptAttackCalculator
from tetris.attack.tetrio_s1 import TetrioS1AttackCalculator
from tetris.attack.tetrio_s2 import TetrioS2AttackCalculator
from tetris.game.state import AppliedMove


class AttackCalculator(Protocol):
    def calculate(self, applied: AppliedMove) -> int: ...


_ATTACK_CALCULATORS: dict[str, type[AttackCalculator]] = {
    "tetrio_s1": TetrioS1AttackCalculator,
    "tetrio_s2": TetrioS2AttackCalculator,
    "ppt": PptAttackCalculator,
    "classic_guideline": ClassicGuidelineAttackCalculator,
    "modern_guideline": ModernGuidelineAttackCalculator,
}


def register_attack_calculator(name: str, calculator: type[AttackCalculator]) -> None:
    if name in _ATTACK_CALCULATORS:
        raise ValueError(f"Attack calculator already registered: {name!r}")
    _ATTACK_CALCULATORS[name] = calculator


def attack_calculator(name: str) -> type[AttackCalculator]:
    try:
        return _ATTACK_CALCULATORS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown attack calculator: {name!r}") from exc
