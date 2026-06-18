from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int | None


def web_visualizer_endpoint(
    settings: dict[str, Any],
    *,
    host: str | None = None,
    port: int | None = None,
) -> Endpoint:
    web_cfg = settings.get("visualizer", {}).get("web", {})
    return Endpoint(
        host=_host_value("visualizer.web.host", host, web_cfg.get("host")),
        port=_port_value(
            "visualizer.web.port",
            port,
            web_cfg.get("port"),
            allow_none=True,
        ),
    )


def websocket_endpoint(
    settings: dict[str, Any],
    *,
    host: str | None = None,
    port: int | None = None,
) -> Endpoint:
    ws_cfg = settings.get("api", {}).get("websocket", {})
    return Endpoint(
        host=_host_value("api.websocket.host", host, ws_cfg.get("host")),
        port=_port_value(
            "api.websocket.port",
            port,
            ws_cfg.get("port"),
            allow_none=False,
        ),
    )


def _host_value(name: str, override: str | None, configured: object) -> str:
    value = override if override is not None else configured
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _port_value(
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
