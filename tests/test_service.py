from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from typing import Any
from unittest.mock import patch

from tetris.model.board import Board
from tetris.model.location import PieceLocation
from tetris.model.piece import Piece
from tetris.model.placement import Placement
from tetris.model.rotation import Rotation
from tetris.model.spin import Spin
from tetris.model.rules import Rules
from tetris.game.state import GameState, spawn_location
from tetris.movegen.pathfinder import MoveStep
from suggestion.session.client_session import ClientSession
from suggestion.move_selection import pick_move
from suggestion.piece_stream_tracker import PieceStreamTracker
from suggestion.contracts.bot_snapshot import BotSnapshot
from suggestion.contracts.observed_snapshot import ObservedSnapshot
from suggestion.contracts.suggestion_request import SuggestionRequest
from suggestion.contracts.suggestion_status import SuggestionStatus
from protocols.sbp.messages import BotCapabilities


def placement(
    piece: Piece, x: int, y: int, rotation: Rotation = Rotation.North
) -> Placement:
    return Placement(PieceLocation(piece, rotation, x, y), Spin.none)


def snapshot(
    board: Board | None = None,
    active: Piece | None = None,
    queue: list[Piece] | None = None,
    seq: int = 0,
    last_move: Placement | None = None,
) -> ObservedSnapshot:
    active_piece = active or Piece.O
    pieces = queue or [Piece.I, Piece.T, Piece.L, Piece.J]
    return ObservedSnapshot(
        board=board or Board(),
        active=spawn_location(active_piece),
        queue=list(pieces),
        hold=None,
        can_hold=True,
        seq=seq,
        last_move=last_move,
    )


class FakeBotSession:
    def __init__(self, suggestions: list[list[Placement]]) -> None:
        self.suggestions = suggestions
        self.started: list[BotSnapshot] = []
        self.started_rules: list[Rules] = []
        self.resets: list[BotSnapshot] = []
        self.reset_rules: list[Rules] = []
        self.advanced: list[tuple[Placement, list[Piece]]] = []
        self.suggested_extensions: list[dict[str, Any] | None] = []
        self.stopped = False
        self.closed = False

    def start_from(self, snapshot: BotSnapshot, rules: Rules) -> None:
        self.started.append(snapshot)
        self.started_rules.append(rules)

    def suggest(
        self, timeout_ms: int, extensions: dict[str, Any] | None = None
    ) -> list[Placement]:
        self.suggested_extensions.append(extensions)
        if not self.suggestions:
            return []
        return self.suggestions.pop(0)

    def advance_with(
        self, placement: Placement, new_pieces: list[Piece] | None = None
    ) -> None:
        self.advanced.append((placement, list(new_pieces or [])))

    def reset_from(self, snapshot: BotSnapshot, rules: Rules) -> None:
        self.resets.append(snapshot)
        self.reset_rules.append(rules)

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class ServiceTests(unittest.TestCase):
    def test_pick_move_accepts_5_piece_hold_candidate(self) -> None:
        snap = snapshot(active=Piece.O, queue=[Piece.I, Piece.T, Piece.L, Piece.J])
        self.assertEqual(
            pick_move([placement(Piece.I, 4, 0)], snap), placement(Piece.I, 4, 0)
        )

    def test_game_state_queue_excludes_active(self) -> None:
        state = GameState(
            Board(), spawn_location(Piece.O), [Piece.I, Piece.T], None, 0, 0
        )

        self.assertEqual(state.active.piece, Piece.O)
        self.assertEqual(state.queue, [Piece.I, Piece.T])

    def test_apply_move_success_spawns_next_active(self) -> None:
        state = GameState(
            Board(), spawn_location(Piece.O), [Piece.I, Piece.T], None, 0, 0
        )

        self.assertTrue(state.apply_move(placement(Piece.O, 4, 0), Rules()))

        self.assertEqual(state.active.piece, Piece.I)
        self.assertEqual(state.queue, [Piece.T])

    def test_apply_move_uses_custom_spawn_position_for_next_active(self) -> None:
        state = GameState(
            Board(), spawn_location(Piece.O), [Piece.I, Piece.T], None, 0, 0
        )

        self.assertTrue(
            state.apply_move(placement(Piece.O, 4, 0), Rules(spawn_x=5, spawn_y=18))
        )

        self.assertEqual(state.active, spawn_location(Piece.I, x=5, y=18))

    def test_apply_move_failure_does_not_mutate_active_queue_or_hold(self) -> None:
        state = GameState(
            Board(), spawn_location(Piece.O), [Piece.I, Piece.T], None, 0, 0
        )
        before_active = state.active
        before_queue = list(state.queue)
        before_hold = state.hold

        self.assertFalse(state.apply_move(placement(Piece.O, 20, 0), Rules()))

        self.assertEqual(state.active, before_active)
        self.assertEqual(state.queue, before_queue)
        self.assertEqual(state.hold, before_hold)

    def test_first_snapshot_starts_bot_with_normalized_state(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)]])
        session = ClientSession(lambda: fake)

        result = session.suggest(SuggestionRequest(snapshot=snapshot(), rules=Rules()))

        self.assertEqual(result.status, SuggestionStatus.Synced)
        self.assertEqual(result.placement, placement(Piece.O, 4, 0))
        self.assertEqual(fake.started[0].active, Piece.O)
        self.assertEqual(fake.started[0].queue, [Piece.I, Piece.T, Piece.L, Piece.J])
        self.assertIsNotNone(fake.started[0].piece_stream)
        assert fake.started[0].piece_stream is not None
        self.assertEqual(fake.started[0].piece_stream.offset, 0)
        self.assertEqual(
            fake.started[0].piece_stream.pieces,
            [Piece.O, Piece.I, Piece.T, Piece.L, Piece.J],
        )
        self.assertEqual(fake.started[0].combo, 0)
        self.assertEqual(fake.started[0].back_to_back, 0)

    def test_extensions_are_forwarded_to_start_and_suggest(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)]])
        session = ClientSession(lambda: fake)
        extensions = {"minorail.garbage.v1": {"incoming_garbage": 4}}

        session.suggest(
            SuggestionRequest(
                snapshot=snapshot(),
                rules=Rules(),
                extensions=extensions,
            )
        )

        self.assertEqual(fake.started[0].extensions, extensions)
        self.assertIsNot(fake.started[0].extensions, extensions)
        self.assertEqual(fake.suggested_extensions, [extensions])

    def test_expected_transition_advances_bot_with_new_piece(self) -> None:
        first = placement(Piece.O, 4, 0)
        second = placement(Piece.I, 0, 2, Rotation.East)
        fake = FakeBotSession([[first], [second]])
        session = ClientSession(lambda: fake)
        rules = Rules()

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=rules))
        state = GameState(
            Board(),
            spawn_location(Piece.O),
            [Piece.I, Piece.T, Piece.L, Piece.J],
            None,
            0,
            0,
        )
        self.assertTrue(state.apply_move(first, rules))
        state.queue.append(Piece.S)

        result = session.suggest(
            SuggestionRequest(
                snapshot=snapshot(
                    state.board,
                    active=state.active.piece,
                    queue=state.queue,
                    seq=1,
                    last_move=first,
                ),
                rules=rules,
            )
        )

        self.assertEqual(result.status, SuggestionStatus.Advanced)
        self.assertEqual(fake.advanced, [(first, [Piece.S])])
        stream = session.piece_stream.snapshot()
        self.assertIsNotNone(stream)
        assert stream is not None
        self.assertEqual(stream.offset, 0)
        self.assertEqual(
            stream.pieces, [Piece.O, Piece.I, Piece.T, Piece.L, Piece.J, Piece.S]
        )

    def test_same_rules_and_same_snapshot_keep_bot_session(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)], [placement(Piece.O, 4, 0)]])
        session = ClientSession(lambda: fake)
        rules = Rules(rot180=True)

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=rules))
        result = session.suggest(
            SuggestionRequest(snapshot=snapshot(seq=1), rules=rules)
        )

        self.assertEqual(result.status, SuggestionStatus.Synced)
        self.assertEqual(len(fake.started), 1)
        self.assertEqual(fake.started_rules, [rules])
        self.assertEqual(fake.resets, [])
        self.assertEqual(fake.advanced, [])

    def test_rules_change_resets_bot_session_before_suggesting(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)], [placement(Piece.O, 4, 0)]])
        session = ClientSession(lambda: fake)
        old_rules = Rules(rot180=True)
        new_rules = Rules(rot180=False)

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=old_rules))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = session.suggest(
                SuggestionRequest(snapshot=snapshot(seq=1), rules=new_rules)
            )

        self.assertEqual(result.status, SuggestionStatus.Resynced)
        self.assertIn("type=rules_changed", stderr.getvalue())
        self.assertEqual(len(fake.started), 1)
        self.assertEqual(len(fake.resets), 1)
        self.assertEqual(fake.reset_rules, [new_rules])
        self.assertEqual(fake.advanced, [])

    def test_rules_change_preserves_unexpected_piece_stream_resync(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)], [placement(Piece.T, 4, 0)]])
        session = ClientSession(lambda: fake)
        old_rules = Rules(rot180=True)
        new_rules = Rules(rot180=False)

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=old_rules))
        changed = snapshot(
            active=Piece.T, queue=[Piece.L, Piece.J, Piece.S, Piece.Z], seq=1
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = session.suggest(
                SuggestionRequest(snapshot=changed, rules=new_rules)
            )

        self.assertEqual(result.status, SuggestionStatus.Resynced)
        self.assertIn(
            "type=rules_changed seq=1 bot_action=reset piece_stream_action=resync",
            stderr.getvalue(),
        )
        self.assertEqual(len(fake.resets), 1)
        self.assertEqual(fake.reset_rules, [new_rules])
        stream = fake.resets[0].piece_stream
        self.assertIsNotNone(stream)
        assert stream is not None
        self.assertIsNone(stream.offset)
        self.assertEqual(stream.pieces, [Piece.T, Piece.L, Piece.J, Piece.S, Piece.Z])

    def test_board_desync_resets_bot_without_losing_piece_stream_offset(self) -> None:
        fake = FakeBotSession(
            [[placement(Piece.O, 4, 0)], [placement(Piece.I, 0, 2, Rotation.East)]]
        )
        session = ClientSession(lambda: fake)
        rules = Rules()

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=rules))
        changed = snapshot(
            active=Piece.I, queue=[Piece.T, Piece.L, Piece.J, Piece.S], seq=1
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = session.suggest(SuggestionRequest(snapshot=changed, rules=rules))

        self.assertEqual(result.status, SuggestionStatus.Resynced)
        self.assertIn(
            "[info] minorail resync: type=board_changed_after_expected_advance seq=1 "
            "bot_action=reset piece_stream_action=append",
            stderr.getvalue(),
        )
        self.assertEqual(len(fake.resets), 1)
        stream = fake.resets[0].piece_stream
        self.assertIsNotNone(stream)
        assert stream is not None
        self.assertEqual(stream.offset, 0)
        self.assertEqual(
            stream.pieces, [Piece.O, Piece.I, Piece.T, Piece.L, Piece.J, Piece.S]
        )

    def test_unexpected_piece_chronology_resets_piece_stream_offset(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)], [placement(Piece.T, 4, 0)]])
        session = ClientSession(lambda: fake)
        rules = Rules()

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=rules))
        changed = snapshot(
            active=Piece.T, queue=[Piece.L, Piece.J, Piece.S, Piece.Z], seq=1
        )
        result = session.suggest(SuggestionRequest(snapshot=changed, rules=rules))

        self.assertEqual(result.status, SuggestionStatus.Resynced)
        self.assertEqual(len(fake.resets), 1)
        stream = fake.resets[0].piece_stream
        self.assertIsNotNone(stream)
        assert stream is not None
        self.assertIsNone(stream.offset)
        self.assertEqual(stream.pieces, [Piece.T, Piece.L, Piece.J, Piece.S, Piece.Z])

    def test_piece_stream_trimming_adjusts_offset(self) -> None:
        tracker = PieceStreamTracker(limit=5)
        tracker.initialize([Piece.O, Piece.I, Piece.T, Piece.L, Piece.J])
        tracker.append([Piece.S, Piece.Z])

        stream = tracker.snapshot()
        self.assertIsNotNone(stream)
        assert stream is not None
        self.assertEqual(stream.offset, 2)
        self.assertEqual(stream.pieces, [Piece.T, Piece.L, Piece.J, Piece.S, Piece.Z])

    def test_piece_stream_limit_zero_omits_stream(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)]])
        session = ClientSession(lambda: fake, piece_stream_limit=0)

        session.suggest(SuggestionRequest(snapshot=snapshot(), rules=Rules()))

        self.assertIsNone(fake.started[0].piece_stream)

    def test_convert_sonic_drops_request_option_rewrites_path(self) -> None:
        fake = FakeBotSession([[placement(Piece.O, 4, 0)]])
        session = ClientSession(lambda: fake)

        with patch(
            "suggestion.session.client_session.find_path",
            return_value=[MoveStep.SonicDrop, MoveStep.HardDrop],
        ):
            result = session.suggest(
                SuggestionRequest(
                    snapshot=snapshot(active=Piece.O),
                    rules=Rules(sonic_drop="only"),
                    convert_sonic_drops=True,
                )
            )

        self.assertIsNotNone(result.path)
        assert result.path is not None
        self.assertNotIn(MoveStep.SonicDrop, result.path)
        self.assertEqual(result.path.count(MoveStep.SoftDrop), 19)

    def test_going_idle_closes_bot_and_restarts_from_snapshot(self) -> None:
        class FakeTimer:
            instances: list["FakeTimer"] = []

            def __init__(self, timeout: float, callback: Any, args: list[Any]) -> None:
                self.timeout = timeout
                self.callback = callback
                self.args = args
                self.daemon = False
                self.cancelled = False
                FakeTimer.instances.append(self)

            def start(self) -> None:
                pass

            def cancel(self) -> None:
                self.cancelled = True

            def fire(self) -> None:
                self.callback(*self.args)

        first_move = placement(Piece.O, 4, 0)
        fake = FakeBotSession([[first_move], [placement(Piece.I, 0, 2, Rotation.East)]])
        with patch("suggestion.session.client_session.threading.Timer", FakeTimer):
            session = ClientSession(lambda: fake, idle_ms=60_000)
            rules = Rules()

            first = session.suggest(SuggestionRequest(snapshot=snapshot(), rules=rules))
            state = GameState(
                Board(),
                spawn_location(Piece.O),
                [Piece.I, Piece.T, Piece.L, Piece.J],
                None,
                0,
                0,
            )
            self.assertTrue(state.apply_move(first_move, rules))
            state.queue.append(Piece.S)
            advanced = snapshot(
                state.board,
                active=state.active.piece,
                queue=state.queue,
                seq=1,
                last_move=first_move,
            )
            FakeTimer.instances[-1].fire()
            second = session.suggest(SuggestionRequest(snapshot=advanced, rules=rules))

        self.assertEqual(first.status, SuggestionStatus.Synced)
        self.assertEqual(second.status, SuggestionStatus.Advanced)
        self.assertTrue(fake.closed)
        self.assertEqual(len(fake.started), 2)
        self.assertEqual(fake.advanced, [])
        self.assertEqual(fake.resets, [])
        stream = fake.started[1].piece_stream
        self.assertIsNotNone(stream)
        assert stream is not None
        self.assertEqual(stream.offset, 0)
        self.assertEqual(
            stream.pieces, [Piece.O, Piece.I, Piece.T, Piece.L, Piece.J, Piece.S]
        )

    def test_capabilities_validate_configured_rules(self) -> None:
        capabilities = BotCapabilities.from_sbp(
            {
                "randomizers": ["seven_bag"],
                "kicksets": ["srs"],
                "rot180": True,
                "sonic_drop": ["only", "allow"],
                "piece_stream": True,
                "spawn_position": True,
            }
        )

        self.assertIsNone(capabilities.validate_rules(Rules()))
        self.assertTrue(capabilities.piece_stream)

    def test_capabilities_reject_custom_spawn_without_support(self) -> None:
        capabilities = BotCapabilities.from_sbp(
            {
                "randomizers": ["seven_bag"],
                "kicksets": ["srs"],
                "rot180": True,
                "sonic_drop": ["only"],
            }
        )

        error = capabilities.validate_rules(Rules(spawn_x=5))

        self.assertEqual(error, "bot does not support custom spawn_position")

    def test_capabilities_reject_unsupported_rule(self) -> None:
        capabilities = BotCapabilities.from_sbp(
            {
                "randomizers": ["seven_bag"],
                "kicksets": ["srs"],
                "rot180": False,
                "sonic_drop": ["only"],
            }
        )

        error = capabilities.validate_rules(Rules(rot180=True))

        self.assertEqual(error, "bot does not support rot180")


if __name__ == "__main__":
    unittest.main()
