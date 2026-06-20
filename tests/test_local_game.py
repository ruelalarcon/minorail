import unittest

from solo.runner.local_game import LocalGame
from tetris.game.state import GameState, spawn_location
from tetris.model.board import Board
from tetris.model.piece import Piece
from tetris.model.rules import Rules


class FakeRandomizer:
    def next(self) -> Piece:
        return Piece.I

    def peek_bag(self) -> list[Piece]:
        return []


class LocalGameTests(unittest.TestCase):
    def test_topout_when_active_spawn_cell_is_occupied(self) -> None:
        board = Board()
        board.cols[4] |= 1 << 19
        game = _game(board, active=Piece.O)

        self.assertTrue(game.is_topped_out())

    def test_high_cell_outside_active_spawn_is_not_topout(self) -> None:
        board = Board()
        board.cols[0] |= 1 << 25
        game = _game(board, active=Piece.O)

        self.assertFalse(game.is_topped_out())


def _game(board: Board, *, active: Piece) -> LocalGame:
    return LocalGame(
        state=GameState(
            board=board,
            active=spawn_location(active),
            queue=[Piece.I],
            hold=None,
            combo=0,
            back_to_back=0,
        ),
        rules=Rules(),
        randomizer=FakeRandomizer(),
    )


if __name__ == "__main__":
    unittest.main()
