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
    def from_values(values: dict[str, Any]) -> Rules:
        return Rules(
            randomizer=values.get("randomizer", "seven_bag"),
            kickset=values.get("kickset", "srs"),
            rot180=values.get("rot180", True),
            sonic_drop=values.get("sonic_drop", "only"),
            allspin_b2b=values.get("allspin_b2b", False),
            allclear_b2b=values.get("allclear_b2b", False),
            spawn_x=values.get("spawn_x", 4),
            spawn_y=values.get("spawn_y", 19),
        )
