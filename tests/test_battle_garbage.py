import unittest

from battle.garbage.generic import GenericGarbageRules
from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board
from tetris.model.piece import Piece


def _hole_at_row(state: GameState, y: int) -> int:
    holes = [x for x, col in enumerate(state.board.cols) if not col & (1 << y)]
    assert len(holes) == 1
    return holes[0]


class GenericGarbageRulesTests(unittest.TestCase):
    def test_full_cancellation_blocks_attack_before_sending(self) -> None:
        rules = GenericGarbageRules(seed=123)
        queue = rules.enqueue_attack(rules.empty_queue(), attack=4)

        exchange = rules.exchange(attack=6, queue=queue)

        self.assertEqual(exchange.cancelled, 4)
        self.assertEqual(exchange.sent, 2)
        self.assertEqual(rules.queue_total(exchange.queue_after), 0)

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
        queue = rules.enqueue_attack(rules.empty_queue(), attack=12)

        applied = rules.apply_queue(state, queue)

        self.assertEqual(applied.lines, 8)
        self.assertFalse(applied.topped_out)
        self.assertEqual(rules.queue_total(applied.queue_after), 4)
        self.assertEqual(sum(col.bit_count() for col in state.board.cols), 8 * 9)

    def test_each_attack_packet_uses_one_hole_column(self) -> None:
        rules = GenericGarbageRules(seed=123)
        state = GameState(
            board=Board(),
            active=spawn_location(Piece.I),
            queue=[Piece.O],
            hold=None,
            combo=0,
            back_to_back=0,
        )
        queue = rules.enqueue_attack(rules.empty_queue(), attack=4)
        queue = rules.enqueue_attack(queue, attack=2)

        applied = rules.apply_queue(state, queue)
        row_holes = [_hole_at_row(state, y) for y in range(6)]

        self.assertEqual(applied.lines, 6)
        self.assertEqual(rules.queue_total(applied.queue_after), 0)
        self.assertEqual(row_holes[:4], [row_holes[0]] * 4)
        self.assertEqual(row_holes[4:], [row_holes[4]] * 2)


if __name__ == "__main__":
    unittest.main()
