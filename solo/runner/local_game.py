from __future__ import annotations

from dataclasses import dataclass

from solo.runner.controls import CellEdit
from contracts.observed_snapshot import ObservedSnapshot
from tetris.game.state import AppliedMove, GameState, spawn_location
from tetris.model.board import Board
from tetris.model.placement import Placement
from tetris.model.rules import Rules
from tetris.randomizer import Randomizer


@dataclass
class LocalGame:
    state: GameState
    rules: Rules
    randomizer: Randomizer
    seq: int = 0
    last_move: Placement | None = None

    @classmethod
    def start(
        cls,
        *,
        rules: Rules,
        randomizer: Randomizer,
        initial_pieces: int,
    ) -> LocalGame:
        active = spawn_location(
            randomizer.next(),
            x=rules.spawn_x,
            y=rules.spawn_y,
        )
        return cls(
            state=GameState(
                board=Board.empty(rules.board_width, rules.board_height),
                active=active,
                queue=[randomizer.next() for _ in range(max(0, initial_pieces - 1))],
                hold=None,
                combo=0,
                back_to_back=0,
            ),
            rules=rules,
            randomizer=randomizer,
        )

    def snapshot(self) -> ObservedSnapshot:
        return ObservedSnapshot(
            board=self.state.board.copy(),
            active=self.state.active,
            queue=list(self.state.queue),
            hold=self.state.hold,
            can_hold=not self.state.hold_used_this_turn,
            seq=self.seq,
            last_move=self.last_move,
        )

    def advance_seq(self) -> None:
        self.seq += 1

    def refill_queue(self, threshold: int) -> None:
        while len(self.state.queue) < threshold:
            self.state.queue.append(self.randomizer.next())

    def apply_placement(self, placement: Placement) -> AppliedMove | None:
        applied = self.state.apply_move(placement, self.rules)
        if applied is not None:
            self.last_move = placement
        return applied

    def set_cell(self, x: int, y: int, filled: bool) -> None:
        self.set_cells([CellEdit(x, y, filled)])

    def set_cells(self, edits: list[CellEdit]) -> None:
        changed = False
        for edit in edits:
            _validate_cell(edit.x, edit.y, self.state.board)
            mask = 1 << edit.y
            was_filled = bool(self.state.board.cols[edit.x] & mask)
            if was_filled == edit.filled:
                continue
            if edit.filled:
                self.state.board.cols[edit.x] |= mask
            else:
                self.state.board.cols[edit.x] &= ~mask
            changed = True

        if changed:
            self.advance_seq()
            self.last_move = None

    def clear_board(self) -> None:
        edits = [
            CellEdit(x, y, False)
            for x in range(self.state.board.width)
            for y in range(self.state.board.height)
            if self.state.board.cols[x] & (1 << y)
        ]
        self.set_cells(edits)

    def is_topped_out(self) -> bool:
        return any(
            0 <= x < self.state.board.width
            and 0 <= y < self.state.board.height
            and self.state.board.occupied(x, y)
            for x, y in self.state.active.cells()
        )


def _validate_cell(x: int, y: int, board: Board | None = None) -> None:
    width = 10 if board is None else board.width
    height = 40 if board is None else board.height
    if x < 0 or x >= width or y < 0 or y >= height:
        raise ValueError(f"cell out of bounds: ({x}, {y})")
