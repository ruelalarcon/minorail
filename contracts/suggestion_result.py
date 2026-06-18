from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from contracts.suggestion_status import SuggestionStatus
from tetris.model.placement import Placement
from tetris.movegen.steps import MoveStep


@dataclass
class SuggestionResult:
    seq: int
    status: SuggestionStatus
    placements: list[Placement]
    placement: Optional[Placement]
    path: Optional[list[MoveStep]]
    reason: Optional[str] = None
