from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.location import PieceLocation
from core.spin import Spin


@dataclass
class Placement:
    location: PieceLocation
    spin: Spin

    def to_tbp(self) -> dict[str, Any]:
        return {"location": self.location.to_tbp(), "spin": self.spin.value}

    @staticmethod
    def from_tbp(d: dict[str, Any]) -> Placement:
        return Placement(
            location=PieceLocation.from_tbp(d["location"]),
            spin=Spin(d["spin"]),
        )
