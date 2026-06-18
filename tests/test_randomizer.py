import random
import unittest

from tetris.model.piece import Piece
from tetris.randomizer import Randomizer, PureRandom, SevenBag, make_randomizer


class TestRandomizerSeeds(unittest.TestCase):
    def test_seven_bag_seed_repeats_stream(self) -> None:
        first = SevenBag(seed=123)
        second = SevenBag(seed=123)

        self.assertEqual(_draw(first, 28), _draw(second, 28))

    def test_pure_random_seed_repeats_stream(self) -> None:
        first = PureRandom(seed=123)
        second = PureRandom(seed=123)

        self.assertEqual(_draw(first, 28), _draw(second, 28))

    def test_randomizers_do_not_use_global_random_state(self) -> None:
        random.seed(1)
        first = SevenBag(seed=123)
        first_pieces = _draw(first, 28)

        random.seed(999)
        second = SevenBag(seed=123)
        second_pieces = _draw(second, 28)

        self.assertEqual(first_pieces, second_pieces)

    def test_make_randomizer_passes_seed(self) -> None:
        first = make_randomizer("seven_bag", seed=123)
        second = make_randomizer("seven_bag", seed=123)

        assert first is not None
        assert second is not None
        self.assertEqual(_draw(first, 28), _draw(second, 28))


def _draw(randomizer: Randomizer, count: int) -> list[Piece]:
    return [randomizer.next() for _ in range(count)]
