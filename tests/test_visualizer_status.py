import unittest

from visualizers.shared.status import VisualizerStatus


class VisualizerStatusTests(unittest.TestCase):
    def test_battle_topout_uses_win_loss_statuses(self) -> None:
        status = VisualizerStatus(("A", "B"))

        status.end_battle(status="topout", winner="A", loser="B")

        self.assertEqual(status.player("A"), "Win")
        self.assertEqual(status.player("B"), "Loss")

    def test_battle_limit_uses_ended_status_for_each_player(self) -> None:
        status = VisualizerStatus(("A", "B"))

        status.end_battle(status="piece_limit", winner=None, loser=None)

        self.assertEqual(status.player("A"), "Ended: piece_limit")
        self.assertEqual(status.player("B"), "Ended: piece_limit")


if __name__ == "__main__":
    unittest.main()
