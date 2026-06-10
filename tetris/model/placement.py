from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tetris.model.location import PieceLocation
from tetris.model.spin import Spin


@dataclass
class Placement:
    location: PieceLocation
    spin: Spin

    def to_sbp(self) -> dict[str, Any]:
        return {"location": self.location.to_sbp(), "spin": self.spin.value}

    @staticmethod
    def from_sbp(d: dict[str, Any]) -> Placement:
        return Placement(
            location=PieceLocation.from_sbp(d["location"]),
            spin=Spin(d["spin"]),
        )
