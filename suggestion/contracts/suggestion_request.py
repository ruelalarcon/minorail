from dataclasses import dataclass

from tetris.model.rules import Rules
from suggestion.contracts.observed_snapshot import ObservedSnapshot


@dataclass
class SuggestionRequest:
    snapshot: ObservedSnapshot
    rules: Rules
    include_path: bool = True
    convert_sonic_drops: bool = False
    session_id: str = "default"
    timeout_ms: int = 10_000
