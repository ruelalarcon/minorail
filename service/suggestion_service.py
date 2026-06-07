from __future__ import annotations

from typing import Callable

from service.bot_session import BotSession
from service.client_session import ClientSession
from service.snapshot import SuggestionRequest, SuggestionResult


class SuggestionService:
    def __init__(self, bot_path: str) -> None:
        self._bot_path = bot_path
        self._sessions: dict[str, ClientSession] = {}

    def suggest(self, request: SuggestionRequest) -> SuggestionResult:
        session = self._sessions.get(request.session_id)
        if session is None:
            session = ClientSession(self._bot_session_factory())
            self._sessions[request.session_id] = session
        return session.suggest(request)

    def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.close()

    def close(self) -> None:
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()

    def _bot_session_factory(self) -> Callable[[], BotSession]:
        return lambda: BotSession(self._bot_path)
