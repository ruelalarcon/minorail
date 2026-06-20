from __future__ import annotations


class VisualizerStatus:
    def __init__(self, players: tuple[str, ...] = ()) -> None:
        self._players = players
        self._status = ""
        self._player_statuses = {player: "" for player in players}

    @property
    def text(self) -> str:
        return self._status

    def set(self, status: str) -> None:
        self._status = status

    def reset_players(self, status: str = "") -> None:
        self._player_statuses = {player: status for player in self._players}

    def set_player(self, player: str, status: str) -> None:
        self._player_statuses[player] = status

    def set_all_players(self, status: str) -> None:
        for player in self._players:
            self._player_statuses[player] = status

    def end_battle(
        self,
        *,
        status: str,
        winner: str | None,
        loser: str | None,
    ) -> None:
        if status == "topout" and winner is not None and loser is not None:
            self._player_statuses[winner] = "Win"
            self._player_statuses[loser] = "Loss"
            return
        self.set_all_players(f"Ended: {status}")

    def player(self, player: str) -> str:
        return self._player_statuses.get(player, "")
