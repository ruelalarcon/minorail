from __future__ import annotations

from typing import Callable

from bots.session import BotSession
from contracts.suggestion_request import SuggestionRequest
from contracts.suggestion_result import SuggestionResult
from suggestion.session.continuity import SuggestionContinuity


class SuggestionService:
    def __init__(
        self,
        bot_path: str,
        bot_args: list[str] | None = None,
        piece_stream_limit: int = 11,
        info_print_topics: list[str] | None = None,
        idle_ms: int = 60_000,
    ) -> None:
        self._bot_path = bot_path
        self._bot_args = bot_args or []
        self._piece_stream_limit = piece_stream_limit
        self._idle_ms = idle_ms
        self._info_print_topics = {
            topic for topic in info_print_topics or [] if isinstance(topic, str)
        }
        self._sessions: dict[str, SuggestionContinuity] = {}

    def suggest(self, request: SuggestionRequest) -> SuggestionResult:
        session = self._sessions.get(request.session_id)
        if session is None:
            session = SuggestionContinuity(
                self._bot_session_factory(),
                piece_stream_limit=self._piece_stream_limit,
                idle_ms=self._idle_ms,
            )
            self._sessions[request.session_id] = session
        return session.suggest(request)

    def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.close()

    def stop_game(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.stop_game()

    def close(self) -> None:
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()

    def _bot_session_factory(self) -> Callable[[], BotSession]:
        return lambda: BotSession(
            self._bot_path,
            bot_args=self._bot_args,
            info_print_topics=self._info_print_topics,
        )
