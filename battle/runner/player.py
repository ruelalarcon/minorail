from __future__ import annotations

from dataclasses import dataclass

from contracts.observed_snapshot import ObservedSnapshot
from contracts.suggestion_request import SuggestionRequest
from contracts.suggestion_result import SuggestionResult
from settings import PathSettings, Settings
from solo.runner.local_game import LocalGame
from solo.runner.session import SuggestionServiceLike
from tetris.model.rules import Rules
from tetris.randomizer import make_randomizer


@dataclass
class Player:
    name: str
    game: LocalGame
    service: SuggestionServiceLike
    suggestion_session_id: str

    @classmethod
    def start(
        cls,
        *,
        name: str,
        settings: Settings,
        rules: Rules,
        seed: int | None,
        service: SuggestionServiceLike,
        suggestion_session_id: str,
    ) -> Player:
        randomizer = make_randomizer(rules.randomizer, seed=seed)
        assert randomizer is not None
        return cls(
            name=name,
            game=LocalGame.start(
                rules=rules,
                randomizer=randomizer,
                initial_pieces=settings.game_queue().initial,
            ),
            service=service,
            suggestion_session_id=suggestion_session_id,
        )

    def snapshot(self) -> ObservedSnapshot:
        return self.game.snapshot()

    def suggest(
        self,
        *,
        rules: Rules,
        pathfinding: PathSettings,
        timeout_ms: int,
        incoming_garbage: list[int] | None = None,
    ) -> SuggestionResult:
        return self.service.suggest(
            SuggestionRequest(
                snapshot=self.snapshot(),
                rules=rules,
                incoming_garbage=incoming_garbage,
                pathfinding=pathfinding.pathfinding,
                convert_sonic_drops=pathfinding.convert_sonic_drops,
                session_id=self.suggestion_session_id,
                timeout_ms=timeout_ms,
            )
        )
