from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from typing import Any


DEFAULT: dict[str, Any] = {
    "protocol": {
        "rules": {
            "randomizer": "seven_bag",
            "kickset": "srs",
            "rot180": True,
            "sonic_drop": "only",
            "allspin_b2b": False,
            "allclear_b2b": False,
            "spawn_x": 4,
            "spawn_y": 19,
        },
        "start": {
            "piece_stream_limit": 11,
        },
    },
    "service": {
        "path": {
            "convert_sonic_drops": False,
        },
    },
    "bot": {
        "suggest_timeout_ms": 10_000,
        "idle_ms": 60_000,
    },
    "api": {
        "websocket": {
            "host": "127.0.0.1",
            "port": 8444,
        },
    },
    "game": {
        "randomizer": {
            "seed": None,
        },
        "queue": {
            "initial": 5,
            "refill_threshold": 5,
        },
        "limits": {
            "piece_limit": None,
            "time_limit_ms": None,
        },
    },
    "logging": {
        "bot_info": {
            "print": ["log", "warning"],
        },
    },
    "visualizer": {
        "web": {
            "host": "127.0.0.1",
            "port": None,
        },
        "move_delay_ms": 50,
        "lock_delay_ms": 150,
        "first_move_delay_ms": 200,
        "visible_rows": 20,
        "queue_size": 5,
    },
    "battle": {
        "attack": {
            "calculator": "tetrio_s2",
        },
        "garbage": {
            "rules": "ppt",
        },
    },
}


@dataclass(frozen=True)
class RunLimits:
    piece_limit: int | None = None
    time_limit_ms: int | None = None


@dataclass(frozen=True)
class PathSettings:
    pathfinding: bool
    convert_sonic_drops: bool = False

    def __post_init__(self) -> None:
        if not self.pathfinding and self.convert_sonic_drops:
            object.__setattr__(self, "convert_sonic_drops", False)


@dataclass(frozen=True)
class BindEndpoint:
    host: str
    port: int | None


@dataclass(frozen=True)
class BotSettings:
    suggest_timeout_ms: int
    idle_ms: int


@dataclass(frozen=True)
class QueueSettings:
    initial: int
    refill_threshold: int


@dataclass(frozen=True)
class ProtocolStartSettings:
    piece_stream_limit: int


@dataclass(frozen=True)
class VisualizerSettings:
    move_delay_ms: int
    lock_delay_ms: int
    first_move_delay_ms: int
    visible_rows: int
    queue_size: int


@dataclass(frozen=True)
class BattleAttackSettings:
    calculator: str


@dataclass(frozen=True)
class BattleGarbageSettings:
    rules: str


@dataclass(frozen=True)
class Settings:
    _values: dict[str, Any]

    @classmethod
    def load(cls, path: str = "settings.toml") -> Settings:
        values = _copy_nested(DEFAULT)
        if os.path.exists(path):
            with open(path, "rb") as f:
                _merge_nested(values, tomllib.load(f))
        return cls(values)

    @classmethod
    def from_values(cls, values: dict[str, Any]) -> Settings:
        merged = _copy_nested(DEFAULT)
        _merge_nested(merged, values)
        return cls(merged)

    def rules_values(self) -> dict[str, Any]:
        return dict(self._section("protocol", "rules"))

    def protocol_start(self) -> ProtocolStartSettings:
        cfg = self._section("protocol", "start")
        return ProtocolStartSettings(
            piece_stream_limit=_int(
                "protocol.start.piece_stream_limit",
                cfg.get("piece_stream_limit"),
            )
        )

    def bot(self) -> BotSettings:
        cfg = self._section("bot")
        return BotSettings(
            suggest_timeout_ms=_positive_int(
                "bot.suggest_timeout_ms",
                cfg.get("suggest_timeout_ms"),
            ),
            idle_ms=_positive_int("bot.idle_ms", cfg.get("idle_ms")),
        )

    def bot_info_topics(self) -> list[str]:
        value = self._section("logging", "bot_info").get("print")
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError("logging.bot_info.print must be a list of strings")
        return list(value)

    def game_queue(self) -> QueueSettings:
        cfg = self._section("game", "queue")
        return QueueSettings(
            initial=_positive_int("game.queue.initial", cfg.get("initial")),
            refill_threshold=_positive_int(
                "game.queue.refill_threshold",
                cfg.get("refill_threshold"),
            ),
        )

    def run_limits(
        self,
        *,
        piece_limit: int | None = None,
        time_limit_ms: int | None = None,
    ) -> RunLimits:
        cfg = self._section("game", "limits")
        return RunLimits(
            piece_limit=_optional_positive_int(
                "game.limits.piece_limit",
                piece_limit,
                cfg.get("piece_limit"),
            ),
            time_limit_ms=_optional_positive_int(
                "game.limits.time_limit_ms",
                time_limit_ms,
                cfg.get("time_limit_ms"),
            ),
        )

    def pathfinding(
        self,
        *,
        default_pathfinding: bool,
        pathfinding: bool | None = None,
    ) -> PathSettings:
        cfg = self._section("service", "path")
        resolved_pathfinding = _pathfinding_value(
            pathfinding,
            cfg.get("pathfinding"),
            default_pathfinding,
        )
        convert_sonic_drops = _bool(
            "service.path.convert_sonic_drops",
            cfg.get("convert_sonic_drops", False),
        )
        return PathSettings(
            pathfinding=resolved_pathfinding,
            convert_sonic_drops=convert_sonic_drops if resolved_pathfinding else False,
        )

    def base_seed(self, override: int | None) -> int | None:
        if override is not None:
            return override
        seed = self._section("game", "randomizer").get("seed")
        if seed is None:
            return None
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("game.randomizer.seed must be an integer")
        return seed

    def web_visualizer_endpoint(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
    ) -> BindEndpoint:
        cfg = self._section("visualizer", "web")
        return BindEndpoint(
            host=_host("visualizer.web.host", host, cfg.get("host")),
            port=_port("visualizer.web.port", port, cfg.get("port"), allow_none=True),
        )

    def websocket_endpoint(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
    ) -> BindEndpoint:
        cfg = self._section("api", "websocket")
        return BindEndpoint(
            host=_host("api.websocket.host", host, cfg.get("host")),
            port=_port("api.websocket.port", port, cfg.get("port"), allow_none=False),
        )

    def visualizer(self) -> VisualizerSettings:
        cfg = self._section("visualizer")
        return VisualizerSettings(
            move_delay_ms=_non_negative_int(
                "visualizer.move_delay_ms",
                cfg.get("move_delay_ms"),
            ),
            lock_delay_ms=_non_negative_int(
                "visualizer.lock_delay_ms",
                cfg.get("lock_delay_ms"),
            ),
            first_move_delay_ms=_non_negative_int(
                "visualizer.first_move_delay_ms",
                cfg.get("first_move_delay_ms"),
            ),
            visible_rows=_positive_int(
                "visualizer.visible_rows", cfg.get("visible_rows")
            ),
            queue_size=_positive_int("visualizer.queue_size", cfg.get("queue_size")),
        )

    def battle_attack(self) -> BattleAttackSettings:
        cfg = self._section("battle", "attack")
        calculator = cfg.get("calculator")
        if not isinstance(calculator, str) or calculator == "":
            raise ValueError("battle.attack.calculator must be a non-empty string")
        return BattleAttackSettings(calculator=calculator)

    def battle_garbage(self) -> BattleGarbageSettings:
        cfg = self._section("battle", "garbage")
        rules = cfg.get("rules")
        if not isinstance(rules, str) or rules == "":
            raise ValueError("battle.garbage.rules must be a non-empty string")
        return BattleGarbageSettings(rules=rules)

    def _section(self, *path: str) -> dict[str, Any]:
        value: object = self._values
        name = ".".join(path)
        for part in path:
            if not isinstance(value, dict):
                raise ValueError(f"{name} must be a table")
            value = value.get(part)
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a table")
        return value


def seed_for_game(seed: int | None, game_index: int) -> int | None:
    if seed is None:
        return None
    return seed + game_index


def _copy_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _copy_nested(v) for k, v in value.items()}
    if isinstance(value, list):
        return list(value)
    return value


def _merge_nested(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_nested(target[key], value)
        else:
            target[key] = value


def _optional_positive_int(
    name: str,
    override: int | None,
    configured: object,
) -> int | None:
    value = override if override is not None else configured
    if value is None:
        return None
    return _positive_int(name, value)


def _positive_int(name: str, value: object) -> int:
    value = _int(name, value)
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _non_negative_int(name: str, value: object) -> int:
    value = _int(name, value)
    if value < 0:
        raise ValueError(f"{name} must be at least 0")
    return value


def _int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false")
    return value


def _pathfinding_value(
    override: bool | None,
    configured: object,
    default_pathfinding: bool,
) -> bool:
    if override is not None:
        return override
    if configured is None:
        return default_pathfinding
    if isinstance(configured, bool):
        return configured
    raise ValueError("service.path.pathfinding must be true or false")


def _host(name: str, override: str | None, configured: object) -> str:
    value = override if override is not None else configured
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _port(
    name: str,
    override: int | None,
    configured: object,
    *,
    allow_none: bool,
) -> int | None:
    value = override if override is not None else configured
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{name} must be an integer")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 1 or value > 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return value
