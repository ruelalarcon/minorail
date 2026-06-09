from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tetris.model.placement import Placement
from tetris.movegen.steps import MoveStep
from suggestion.contracts.suggestion_status import SuggestionStatus


@dataclass
class SuggestionResult:
    seq: int
    status: SuggestionStatus
    placements: list[Placement]
    placement: Optional[Placement]
    path: Optional[list[MoveStep]]
    reason: Optional[str] = None
