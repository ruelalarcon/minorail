from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rules:
    randomizer: str = "seven_bag"
    kickset: str = "srs"
    rot180: bool = True
    sonic_drop: str = "only"
    allspin_b2b: bool = False
    allclear_b2b: bool = False
    spawn_x: int = 4
    spawn_y: int = 19

    @staticmethod
    def from_settings(settings: dict[str, Any]) -> Rules:
        protocol = settings.get("protocol", {})
        r = protocol.get("rules", {})
        return Rules(
            randomizer=r.get("randomizer", "seven_bag"),
            kickset=r.get("kickset", "srs"),
            rot180=r.get("rot180", True),
            sonic_drop=r.get("sonic_drop", "only"),
            allspin_b2b=r.get("allspin_b2b", False),
            allclear_b2b=r.get("allclear_b2b", False),
            spawn_x=r.get("spawn_x", 4),
            spawn_y=r.get("spawn_y", 19),
        )
