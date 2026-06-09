from __future__ import annotations

from dataclasses import dataclass

from tetris.model.spin import Spin
from tetris.model.rules import Rules
from tetris.game.state import GameState
from suggestion.contracts.observed_snapshot import ObservedSnapshot


@dataclass
class DerivedState:
    combo: int = 0
    back_to_back: int = 0

    @staticmethod
    def neutral() -> DerivedState:
        return DerivedState()

    @staticmethod
    def from_observed(snapshot: ObservedSnapshot) -> DerivedState:
        return DerivedState(combo=0, back_to_back=0)

    def to_game_state(self, snapshot: ObservedSnapshot) -> GameState:
        return GameState(
            board=snapshot.board.copy(),
            active=snapshot.active,
            queue=list(snapshot.queue),
            hold=snapshot.hold,
            combo=self.combo,
            back_to_back=self.back_to_back,
            hold_used_this_turn=not snapshot.can_hold,
        )

    def advance_from(
        self, before: ObservedSnapshot, after: ObservedSnapshot, rules: Rules
    ) -> None:
        placement = after.last_move
        if placement is None:
            self.combo = 0
            self.back_to_back = 0
            return

        state = self.to_game_state(before)
        if not state.apply_move(placement, rules):
            self.combo = 0
            self.back_to_back = 0
            return

        self.combo = state.combo
        self.back_to_back = state.back_to_back

    def update_from_confirmed(self, state: GameState) -> None:
        self.combo = state.combo
        self.back_to_back = state.back_to_back

    def repair_or_reset(self, snapshot: ObservedSnapshot, rules: Rules) -> None:
        if snapshot.last_move is None:
            self.combo = 0
            self.back_to_back = 0
            return

        # Without a reliable previous board, only conservative metadata is safe.
        if snapshot.last_move.spin != Spin.none and rules.allspin_b2b:
            self.back_to_back = 0
        self.combo = 0
