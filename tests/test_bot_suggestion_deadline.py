"""Suggestion deadlines must cover late replies and the whole retry sequence."""

import math
from unittest.mock import Mock

import pytest

from bots.session import BotSession
from tetris.model.placement import Placement


class Clock:
    now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Replies:
    def __init__(self, session, clock, replies):
        self.session, self.clock, self.replies = session, clock, iter(replies)
        self.waits = []

    def clear(self):
        pass

    def wait(self, timeout):
        self.waits.append(timeout)
        delay, moves = next(self.replies)
        self.clock.now += min(timeout, delay)
        if delay > timeout:
            return False
        self.session._suggestion = moves
        return True


def session_with_replies(monkeypatch, replies):
    clock = Clock()
    monkeypatch.setattr("bots.session.time.monotonic", clock.monotonic)
    monkeypatch.setattr("bots.session.time.sleep", clock.sleep)
    session = BotSession("unused")
    process = Mock()
    monkeypatch.setattr(session, "_bot", process)
    event = Replies(session, clock, replies)
    monkeypatch.setattr(session, "_suggestion_event", event)
    return session, clock, event, process


def move():
    return Placement.from_sbp(
        dict(location=dict(piece="I", orientation="north", x=4, y=0), spin="none")
    )


def test_accepts_reply_after_five_seconds_within_configured_deadline(monkeypatch):
    placement = move()
    session, clock, event, process = session_with_replies(
        monkeypatch, [(6, [placement])]
    )
    assert session.suggest(12000, [3]) == [placement]
    assert clock.now == 6
    assert event.waits == [12]
    process.send_suggest.assert_called_once_with([3], None)


def test_empty_reply_retries_share_one_deadline(monkeypatch):
    placement = move()
    session, clock, event, _ = session_with_replies(
        monkeypatch, [(6, []), (7, [placement])]
    )
    assert session.suggest(12000) == []
    assert clock.now == pytest.approx(12)
    assert event.waits == pytest.approx([12, 5.95])


def test_no_reply_uses_full_requested_timeout(monkeypatch):
    session, clock, event, _ = session_with_replies(monkeypatch, [(math.inf, [])])
    assert session.suggest(12000) == []
    assert clock.now == 12
    assert event.waits == [12]


def test_retry_backoff_does_not_exceed_short_deadline(monkeypatch):
    session, clock, event, _ = session_with_replies(monkeypatch, [(0, [])])
    assert session.suggest(20) == []
    assert clock.now == pytest.approx(0.02)
    assert len(event.waits) == 1
