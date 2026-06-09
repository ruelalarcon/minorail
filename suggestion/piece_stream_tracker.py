from __future__ import annotations

from tetris.model.piece import Piece
from suggestion.contracts.piece_stream_snapshot import PieceStreamSnapshot


class PieceStreamTracker:
    def __init__(self, limit: int = 11) -> None:
        self._limit = max(0, limit)
        self._stream: PieceStreamSnapshot | None = None

    def initialize(self, queue: list[Piece]) -> None:
        self._stream = PieceStreamSnapshot(offset=0, pieces=list(queue))
        self._trim_to_limit()

    def append(self, pieces: list[Piece]) -> None:
        if self._stream is None:
            return
        self._stream.pieces.extend(pieces)
        self._trim_to_limit()

    def resync(self, queue: list[Piece]) -> None:
        self._stream = PieceStreamSnapshot(offset=None, pieces=list(queue))
        self._trim_to_limit()

    def snapshot(self) -> PieceStreamSnapshot | None:
        if self._limit == 0 or self._stream is None:
            return None
        return PieceStreamSnapshot(
            offset=self._stream.offset,
            pieces=list(self._stream.pieces),
        )

    def _trim_to_limit(self) -> None:
        if self._stream is None or self._limit == 0:
            return
        trim = len(self._stream.pieces) - self._limit
        if trim <= 0:
            return
        del self._stream.pieces[:trim]
        if self._stream.offset is not None:
            self._stream.offset += trim
