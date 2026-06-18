from __future__ import annotations

import os
import tomllib
from typing import Any

DEFAULT: dict[str, Any] = {
    "protocol": {
        "rules": {
            "randomizer": "seven_bag",
            "kickset": "srs",
            "rot180": True,
            "sonic_drop": "only",
            "allspin_b2b": False,
            "allclear_b2b": False,
            "spawn_x": 4,
            "spawn_y": 19,
        },
        "start": {
            "piece_stream_limit": 11,
        },
    },
    "service": {
        "path": {
            "convert_sonic_drops": False,
        },
    },
    "bot": {
        "suggest_timeout_ms": 10_000,
        "idle_ms": 60_000,
    },
    "engine": {
        "randomizer": {
            "seed": None,
        },
        "queue": {
            "initial": 5,
            "refill_threshold": 5,
        },
        "limits": {
            "piece_limit": None,
            "time_limit_ms": None,
        },
    },
    "logging": {
        "bot_info": {
            "print": ["log", "warning"],
        },
    },
    "visualizer": {
        "move_delay_ms": 50,
        "lock_delay_ms": 150,
        "first_move_delay_ms": 200,
        "visible_rows": 20,
        "queue_size": 5,
    },
}


def load(path: str = "settings.toml") -> dict[str, Any]:
    settings = _copy_nested(DEFAULT)
    if not os.path.exists(path):
        return settings
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    _merge_nested(settings, raw)
    return settings


def _copy_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _copy_nested(v) for k, v in value.items()}
    if isinstance(value, list):
        return list(value)
    return value


def _merge_nested(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_nested(target[key], value)
        else:
            target[key] = value
