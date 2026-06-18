from __future__ import annotations

from typing import Any


def base_seed(settings: dict[str, Any], override: int | None) -> int | None:
    if override is not None:
        return override
    seed = settings.get("engine", {}).get("randomizer", {}).get("seed")
    if seed is None:
        return None
    if not isinstance(seed, int):
        raise ValueError("engine.randomizer.seed must be an integer")
    return seed


def game_seed(seed: int | None, game_index: int) -> int | None:
    if seed is None:
        return None
    return seed + game_index
