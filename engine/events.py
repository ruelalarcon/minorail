from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EngineEventType(Enum):
    CellsChanged = "cells_changed"
    SnapshotChanged = "snapshot_changed"


@dataclass(frozen=True)
class EngineEvent:
    type: EngineEventType
    seq: int
    data: dict[str, Any]
