from __future__ import annotations

from tetris.kicks.srs import SRS
from tetris.kicks.table import KickTable

_KICK_TABLES: dict[str, KickTable] = {
    "srs": SRS,
}


def register_kick_table(name: str, table: KickTable) -> None:
    if name in _KICK_TABLES:
        raise ValueError(f"Kick table already registered: {name!r}")
    _KICK_TABLES[name] = table


def kick_table(name: str) -> KickTable:
    try:
        return _KICK_TABLES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown kickset: {name!r}") from exc
