from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PathfindingOptions:
    pathfinding: bool
    convert_sonic_drops: bool = False

    def __post_init__(self) -> None:
        if not self.pathfinding and self.convert_sonic_drops:
            object.__setattr__(self, "convert_sonic_drops", False)


def pathfinding_options(
    settings: dict[str, Any],
    *,
    default_pathfinding: bool,
    pathfinding: bool | None = None,
) -> PathfindingOptions:
    path_cfg = settings.get("service", {}).get("path", {})
    resolved_pathfinding = _pathfinding_value(
        pathfinding,
        path_cfg.get("pathfinding"),
        default_pathfinding,
    )
    convert_sonic_drops = _bool_value(
        "service.path.convert_sonic_drops",
        path_cfg.get("convert_sonic_drops", False),
    )
    return PathfindingOptions(
        pathfinding=resolved_pathfinding,
        convert_sonic_drops=convert_sonic_drops if resolved_pathfinding else False,
    )


def _pathfinding_value(
    override: bool | None,
    configured: object,
    default_pathfinding: bool,
) -> bool:
    if override is not None:
        return override
    if configured is None:
        return default_pathfinding
    if isinstance(configured, bool):
        return configured
    raise ValueError("service.path.pathfinding must be true or false")


def _bool_value(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false")
    return value
