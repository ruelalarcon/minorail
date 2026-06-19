import unittest

from battle.garbage.generic import GenericGarbageRules
from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board
from tetris.model.piece import Piece


class GenericGarbageRulesTests(unittest.TestCase):
    def test_full_cancellation_blocks_attack_before_sending(self) -> None:
        rules = GenericGarbageRules(seed=123)

        exchange = rules.exchange(attack=6, incoming=4)

        self.assertEqual(exchange.cancelled, 4)
        self.assertEqual(exchange.sent, 2)
        self.assertEqual(exchange.incoming_after, 0)

    def test_garbage_rises_on_non_clearing_lock_with_cap(self) -> None:
        rules = GenericGarbageRules(seed=123)
        state = GameState(
            board=Board(),
            active=spawn_location(Piece.I),
            queue=[Piece.O],
            hold=None,
            combo=0,
            back_to_back=0,
        )

        applied = rules.apply_pending(state, 12)

        self.assertEqual(applied.lines, 8)
        self.assertFalse(applied.topped_out)
        self.assertEqual(sum(col.bit_count() for col in state.board.cols), 8 * 9)


if __name__ == "__main__":
    unittest.main()
