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
    def from_config(config: dict[str, Any]) -> Rules:
        return Rules(
            randomizer=config.get("randomizer", "seven_bag"),
            kickset=config.get("kickset", "srs"),
            rot180=config.get("rot180", True),
            sonic_drop=config.get("sonic_drop", "only"),
            allspin_b2b=config.get("allspin_b2b", False),
            allclear_b2b=config.get("allclear_b2b", False),
            spawn_x=config.get("spawn_x", 4),
            spawn_y=config.get("spawn_y", 19),
        )
