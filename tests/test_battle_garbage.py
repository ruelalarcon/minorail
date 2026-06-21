import unittest

from battle.garbage.modern import ModernGarbageRules
from battle.garbage.ppt import PptGarbageRules
from battle.garbage.registry import garbage_rules
from battle.garbage.tetrio import TetrioGarbageRules
from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board
from tetris.model.piece import Piece


def _hole_at_row(state: GameState, y: int) -> int:
    holes = [x for x, col in enumerate(state.board.cols) if not col & (1 << y)]
    assert len(holes) == 1
    return holes[0]


class TetrioGarbageRulesTests(unittest.TestCase):
    def test_registry_resolves_built_in_garbage_rules(self) -> None:
        self.assertIs(garbage_rules("tetrio"), TetrioGarbageRules)
        self.assertIs(garbage_rules("ppt"), PptGarbageRules)
        self.assertIs(garbage_rules("modern"), ModernGarbageRules)

    def test_full_cancellation_blocks_attack_before_sending(self) -> None:
        rules = TetrioGarbageRules(seed=123)
        queue = rules.enqueue_attack(rules.empty_queue(), attack=4)

        exchange = rules.exchange(attack=6, queue=queue)

        self.assertEqual(exchange.cancelled, 4)
        self.assertEqual(exchange.sent, 2)
        self.assertEqual(rules.queue_total(exchange.queue_after), 0)

    def test_garbage_rises_on_non_clearing_lock_with_cap(self) -> None:
        rules = TetrioGarbageRules(seed=123)
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

    def test_each_attack_chunk_uses_one_hole_column(self) -> None:
        rules = TetrioGarbageRules(seed=123)
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
        self.assertEqual(rules.queue_chunks(queue), [4, 2])

    def test_tetrio_cancels_from_oldest_garbage_chunk(self) -> None:
        rules = TetrioGarbageRules(seed=123)
        queue = rules.enqueue_attack(rules.empty_queue(), attack=4)
        queue = rules.enqueue_attack(queue, attack=2)

        exchange = rules.exchange(attack=5, queue=queue)

        self.assertEqual(rules.queue_chunks(exchange.queue_after), [1])

    def test_tetrio_applies_from_oldest_garbage_chunk(self) -> None:
        rules = TetrioGarbageRules(seed=123)
        state = GameState(
            Board(), spawn_location(Piece.T), [Piece.I, Piece.O], None, 0, 0
        )
        queue = rules.enqueue_attack(rules.empty_queue(), attack=4)
        queue = rules.enqueue_attack(queue, attack=2)

        applied = rules.apply_queue(state, queue)
        row_holes = [_hole_at_row(state, y) for y in range(6)]

        self.assertEqual(applied.lines, 6)
        self.assertEqual(rules.queue_total(applied.queue_after), 0)
        self.assertEqual(row_holes[:4], [row_holes[0]] * 4)
        self.assertEqual(row_holes[4:], [row_holes[4]] * 2)

    def test_partial_chunk_keeps_same_hole_for_later_rise(self) -> None:
        rules = TetrioGarbageRules(seed=123)
        state = GameState(
            board=Board(),
            active=spawn_location(Piece.I),
            queue=[Piece.O],
            hold=None,
            combo=0,
            back_to_back=0,
        )
        queue = rules.enqueue_attack(rules.empty_queue(), attack=10)

        applied = rules.apply_queue(state, queue)
        first_hole = _hole_at_row(state, 0)
        applied = rules.apply_queue(state, applied.queue_after)

        self.assertEqual(applied.lines, 2)
        self.assertEqual(rules.queue_total(applied.queue_after), 0)
        self.assertEqual(_hole_at_row(state, 8), first_hole)


class PptGarbageRulesTests(unittest.TestCase):
    def test_chunk_can_change_holes_while_rising(self) -> None:
        rules = PptGarbageRules(seed=0)
        state = GameState(
            board=Board(),
            active=spawn_location(Piece.I),
            queue=[Piece.O],
            hold=None,
            combo=0,
            back_to_back=0,
        )
        queue = rules.enqueue_attack(rules.empty_queue(), attack=8)

        applied = rules.apply_queue(state, queue)
        row_holes = [_hole_at_row(state, y) for y in range(8)]

        self.assertEqual(applied.lines, 8)
        self.assertEqual(row_holes, [6, 6, 6, 9, 9, 9, 9, 9])

    def test_cancellation_still_blocks_before_sending(self) -> None:
        rules = PptGarbageRules(seed=123)
        queue = rules.enqueue_attack(rules.empty_queue(), attack=4)

        exchange = rules.exchange(attack=6, queue=queue)

        self.assertEqual(exchange.cancelled, 4)
        self.assertEqual(exchange.sent, 2)
        self.assertEqual(rules.queue_total(exchange.queue_after), 0)


class ModernGarbageRulesTests(unittest.TestCase):
    def test_early_phase_uses_clean_columns_per_chunk(self) -> None:
        rules = ModernGarbageRules(seed=123)
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
        self.assertEqual(row_holes[:4], [row_holes[0]] * 4)
        self.assertEqual(row_holes[4:], [row_holes[4]] * 2)

    def test_late_phase_can_change_holes_inside_chunk(self) -> None:
        rules = ModernGarbageRules(seed=0)
        state = GameState(
            board=Board(),
            active=spawn_location(Piece.I),
            queue=[Piece.O],
            hold=None,
            combo=0,
            back_to_back=0,
        )
        queue = rules.empty_queue()
        for _ in range(150):
            queue = rules.exchange(attack=0, queue=queue).queue_after
        queue = rules.enqueue_attack(queue, attack=8)

        applied = rules.apply_queue(state, queue)
        row_holes = [_hole_at_row(state, y) for y in range(8)]

        self.assertEqual(applied.lines, 8)
        self.assertNotEqual(row_holes, [row_holes[0]] * 8)

    def test_empty_queue_resets_phase_state_for_new_game(self) -> None:
        rules = ModernGarbageRules(seed=0)
        queue = rules.empty_queue()
        for _ in range(150):
            queue = rules.exchange(attack=0, queue=queue).queue_after

        reset = rules.empty_queue()

        self.assertEqual(rules.queue_total(reset), 0)
        self.assertEqual(reset.locks, 0)


if __name__ == "__main__":
    unittest.main()
