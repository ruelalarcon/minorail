from __future__ import annotations

import os
import tomllib
from typing import Any

DEFAULT: dict[str, dict[str, Any]] = {
    "rules": {
        "randomizer": "seven_bag",
        "kickset": "srs",
        "rot180": True,
        "sonic_drop": "only",
        "allspin_b2b": False,
        "allclear_b2b": False,
    },
    "bot": {
        "suggest_timeout_ms": 10_000,
        "first_move_think_ms": 200,
    },
    "queue": {
        "initial": 5,
        "refill_threshold": 5,
    },
    "protocol": {
        "piece_stream_limit": 11,
    },
    "bot_info": {
        "print": ["log", "warning"],
    },
    "display": {
        "move_delay_ms": 50,
        "lock_delay_ms": 150,
        "visible_rows": 20,
        "queue_size": 5,
    },
}


def load(path: str = "settings.toml") -> dict[str, dict[str, Any]]:
    settings = {k: dict(v) for k, v in DEFAULT.items()}
    if not os.path.exists(path):
        return settings
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    for section, values in raw.items():
        if section in settings:
            settings[section].update(values)
        else:
            settings[section] = values
    return settings
