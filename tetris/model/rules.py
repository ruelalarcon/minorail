from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tetris.model.back_to_back_source import BackToBackSource
from tetris.model.spin_detection import SpinDetection

DEFAULT_BACK_TO_BACK_SOURCES = frozenset(
    {BackToBackSource.quad, BackToBackSource.t_spin, BackToBackSource.t_spin_mini}
)


@dataclass(frozen=True)
class Rules:
    randomizer: str = "seven_bag"
    kickset: str = "srs"
    rot180: bool = True
    sonic_drop: str = "only"
    spin_detection: SpinDetection = SpinDetection.t_spins
    back_to_back_sources: frozenset[BackToBackSource] = DEFAULT_BACK_TO_BACK_SOURCES
    spawn_x: int = 4
    spawn_y: int = 19

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "spin_detection",
            _spin_detection_value(self.spin_detection),
        )
        object.__setattr__(
            self,
            "back_to_back_sources",
            _back_to_back_sources_value(self.back_to_back_sources),
        )

    @staticmethod
    def from_values(values: dict[str, Any]) -> Rules:
        return Rules(
            randomizer=values.get("randomizer", "seven_bag"),
            kickset=values.get("kickset", "srs"),
            rot180=values.get("rot180", True),
            sonic_drop=values.get("sonic_drop", "only"),
            spin_detection=values.get("spin_detection", SpinDetection.t_spins),
            back_to_back_sources=values.get(
                "back_to_back_sources", DEFAULT_BACK_TO_BACK_SOURCES
            ),
            spawn_x=values.get("spawn_x", 4),
            spawn_y=values.get("spawn_y", 19),
        )


def _spin_detection_value(value: object) -> SpinDetection:
    if isinstance(value, SpinDetection):
        return value
    if isinstance(value, str):
        return SpinDetection(value)
    raise ValueError("spin_detection must be a string")


def _back_to_back_sources_value(value: object) -> frozenset[BackToBackSource]:
    if isinstance(value, frozenset) and all(
        isinstance(item, BackToBackSource) for item in value
    ):
        return value
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("back_to_back_sources must be a list of strings")
    result: set[BackToBackSource] = set()
    seen: set[str] = set()
    for item in value:
        if isinstance(item, BackToBackSource):
            source = item
        elif isinstance(item, str):
            source = BackToBackSource(item)
        else:
            raise ValueError("back_to_back_sources must be a list of strings")
        if source.value in seen:
            raise ValueError(f"duplicate back_to_back source {source.value!r}")
        seen.add(source.value)
        result.add(source)
    return frozenset(result)
