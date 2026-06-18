from dataclasses import dataclass
from typing import Any

from contracts.observed_snapshot import ObservedSnapshot
from tetris.model.rules import Rules


@dataclass
class SuggestionRequest:
    snapshot: ObservedSnapshot
    rules: Rules
    extensions: dict[str, Any] | None = None
    pathfinding: bool = True
    convert_sonic_drops: bool = False
    session_id: str = "default"
    timeout_ms: int = 10_000
