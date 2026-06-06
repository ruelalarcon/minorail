from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rules:
    randomizer: str = "seven_bag"
    kickset: str = "srs"
    rot180: bool = True
    sonic_drop: str = "only"

    @staticmethod
    def from_settings(settings: dict[str, dict[str, Any]]) -> Rules:
        r = settings.get("rules", {})
        return Rules(
            randomizer=r.get("randomizer", "seven_bag"),
            kickset=r.get("kickset", "srs"),
            rot180=r.get("rot180", True),
            sonic_drop=r.get("sonic_drop", "only"),
        )
