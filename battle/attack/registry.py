from __future__ import annotations

from battle.attack.base import AttackCalculator
from battle.attack.generic import GenericAttackCalculator

_ATTACK_CALCULATORS: dict[str, type[AttackCalculator]] = {
    "generic": GenericAttackCalculator,
}


def register_attack_calculator(name: str, calculator: type[AttackCalculator]) -> None:
    if name in _ATTACK_CALCULATORS:
        raise ValueError(f"Attack calculator already registered: {name!r}")
    _ATTACK_CALCULATORS[name] = calculator


def attack_calculator(name: str) -> type[AttackCalculator]:
    try:
        return _ATTACK_CALCULATORS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown battle attack calculator: {name!r}") from exc
