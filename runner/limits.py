from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EngineLimits:
    piece_limit: int | None = None
    time_limit_ms: int | None = None


def engine_limits(
    settings: dict[str, Any],
    *,
    piece_limit: int | None = None,
    time_limit_ms: int | None = None,
) -> EngineLimits:
    limits = settings.get("engine", {}).get("limits", {})
    return EngineLimits(
        piece_limit=_limit_value(
            "engine.limits.piece_limit",
            piece_limit,
            limits.get("piece_limit"),
        ),
        time_limit_ms=_limit_value(
            "engine.limits.time_limit_ms",
            time_limit_ms,
            limits.get("time_limit_ms"),
        ),
    )


def _limit_value(name: str, override: int | None, configured: object) -> int | None:
    value = override if override is not None else configured
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value
