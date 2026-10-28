"""Differential fixtures executed from the inspected TETR.IO client function."""

import json
from pathlib import Path
import unittest

from battle.garbage.tetrio import TetrioGarbageRules
from tetris.attack.tetrio_s2 import TetrioS2AttackCalculator
from tetris.game.state import AppliedMove
from tetris.game.back_to_back import back_to_back_increment
from tetris.model.back_to_back_source import BackToBackSource
from tetris.model.rules import Rules
from tetris.model.location import PieceLocation
from tetris.model.placement import Placement
from tetris.model.piece import Piece
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "tetrio_packet_oracle.json").read_text()
)


class TetrioPacketOracleTests(unittest.TestCase):
    def test_b2b_credits_match_executed_client_counter_code(self) -> None:
        rules = Rules(back_to_back_sources=frozenset(BackToBackSource))
        for case in FIXTURES["b2b_cases"]:
            with self.subTest(input=case["input"]):
                source = case["input"]
                credit = back_to_back_increment(
                    Piece(source["piece"].upper()),
                    Spin.full if source["spin"] else Spin.none,
                    source["lines"],
                    source["perfect_clear"],
                    rules,
                )
                after = source["before"] + credit if credit else 0
                self.assertEqual(after, case["expected"])

    def test_packet_offsets_and_opening_bonus_match_client_execution(self) -> None:
        for index, case in enumerate(FIXTURES["cases"]):
            with self.subTest(case=index):
                source, expected = case["input"], case["expected"]
                rules = TetrioGarbageRules(seed=123)
                queue = rules.empty_queue()
                for chunk in source["incoming"]:
                    queue = rules.enqueue_attack(queue, attack=chunk)
                exchange = rules.exchange(
                    attacks=source["attacks"],
                    queue=queue,
                    pieces_placed=source["pieces_placed"],
                    sent_before=source["sent_before"],
                )
                self.assertEqual(exchange.cancelled, expected["cancelled"])
                self.assertEqual(list(exchange.sent_packets), expected["sent_packets"])
                self.assertEqual(
                    rules.queue_chunks(exchange.queue_after),
                    expected["remaining_chunks"],
                )
                self.assertEqual(sum(source["attacks"]), expected["attack"])

    def test_surge_packet_rounding_matches_client_expression(self) -> None:
        calculator = TetrioS2AttackCalculator()
        for case in FIXTURES["surge_segments"]:
            with self.subTest(charge=case["charge"]):
                charge = case["charge"]
                if charge < 4:
                    continue  # Standard versus cannot release these charges.
                applied = AppliedMove(
                    placement=Placement(
                        PieceLocation(Piece.O, Rotation.North, 4, 0), Spin.none
                    ),
                    lines_cleared=1,
                    perfect_clear=False,
                    combo_before=0,
                    combo_after=1,
                    back_to_back_before=charge + 1,
                    back_to_back_after=0,
                )
                self.assertEqual(list(calculator.packets(applied)), case["packets"])


if __name__ == "__main__":
    unittest.main()
