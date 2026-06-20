from __future__ import annotations

from typing import Protocol

from battle.garbage.base import GarbageRules
from battle.garbage.modern import ModernGarbageRules
from battle.garbage.ppt import PptGarbageRules
from battle.garbage.tetrio import TetrioGarbageRules


class GarbageRulesType(Protocol):
    def __call__(self, *, seed: int | None) -> GarbageRules: ...


_GARBAGE_RULES: dict[str, GarbageRulesType] = {
    "modern": ModernGarbageRules,
    "ppt": PptGarbageRules,
    "tetrio": TetrioGarbageRules,
}


def register_garbage_rules(name: str, rules: GarbageRulesType) -> None:
    if name in _GARBAGE_RULES:
        raise ValueError(f"Garbage rules already registered: {name!r}")
    _GARBAGE_RULES[name] = rules


def garbage_rules(name: str) -> GarbageRulesType:
    try:
        return _GARBAGE_RULES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown battle garbage rules: {name!r}") from exc
