import argparse
import asyncio
import shlex
import sys

from runner.engine_session import EngineSession
from runner.endpoints import web_visualizer_endpoint, websocket_endpoint
from runner.limits import engine_limits
from runner.pathfinding import pathfinding_options
from runner.seeding import base_seed, game_seed
import settings as cfg
from suggestion.websocket_api import SuggestionWebSocketServer
from visualizers.headless import HeadlessVisualizer
from visualizers.terminal import TerminalVisualizer
from visualizers.web import WebVisualizer


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=28, width=88)

    def _get_help_string(self, action: argparse.Action) -> str:
        help_text = action.help or ""
        if "%(default)" not in help_text and action.default not in (
            argparse.SUPPRESS,
            None,
            False,
        ):
            help_text += " (default: %(default)s)"
        return help_text


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="minorail",
        description="Run a bot against Minorail's local game engine.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot", metavar="BOT", help="bot executable or script path")

    run_group = parser.add_argument_group("run options")
    run_group.add_argument(
        "--bot-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the bot, as one string; "
        'use = when the value starts with a dash, e.g. --bot-args="--profile --nodes 5000"',
    )
    run_group.add_argument(
        "--games", metavar="N", type=int, default=1, help="games to run"
    )
    run_group.add_argument(
        "--settings",
        metavar="PATH",
        default="settings.toml",
        help="settings TOML file",
    )
    run_group.add_argument(
        "--seed",
        metavar="N",
        type=int,
        default=None,
        help="per-run base seed for reproducible local piece streams; overrides settings",
    )
    run_group.add_argument(
        "--piece-limit",
        metavar="N",
        type=int,
        default=None,
        help="per-run accepted piece lock limit; overrides settings",
    )
    run_group.add_argument(
        "--time-limit-ms",
        metavar="MS",
        type=int,
        default=None,
        help="per-run wall-clock time limit in milliseconds; overrides settings",
    )
    path = run_group.add_mutually_exclusive_group()
    path.add_argument(
        "--pathfind",
        dest="pathfinding",
        action="store_true",
        default=None,
        help="run pathfinding and return input paths; overrides settings",
    )
    path.add_argument(
        "--no-pathfind",
        dest="pathfinding",
        action="store_false",
        default=None,
        help="skip pathfinding and return placements only; overrides settings",
    )

    display_group = parser.add_argument_group("visualization options")
    display = display_group.add_mutually_exclusive_group()
    display.add_argument(
        "--terminal",
        action="store_true",
        help="show the terminal visualizer (default)",
    )
    display.add_argument(
        "--web",
        action="store_true",
        help="show the browser-based visualizer",
    )
    display.add_argument(
        "--headless",
        action="store_true",
        help="run without a visualizer and print periodic progress",
    )
    display_group.add_argument(
        "--web-host",
        metavar="HOST",
        default=None,
        help="host for the web visualizer; overrides settings",
    )
    display_group.add_argument(
        "--web-port",
        metavar="PORT",
        type=int,
        default=None,
        help="port for the web visualizer; overrides settings",
    )
    api_group = parser.add_argument_group("api options")
    api_group.add_argument(
        "--ws",
        action="store_true",
        help="serve suggestions over a websocket API",
    )
    api_group.add_argument(
        "--ws-host",
        metavar="HOST",
        default=None,
        help="host for the websocket API; overrides settings",
    )
    api_group.add_argument(
        "--ws-port",
        metavar="PORT",
        type=int,
        default=None,
        help="port for the websocket API; overrides settings",
    )
    args = parser.parse_args()
    if args.ws and (args.terminal or args.web or args.headless):
        parser.error("--ws cannot be combined with visualization modes")
    if args.ws and args.seed is not None:
        parser.error("--seed cannot be combined with --ws")
    if args.ws and args.piece_limit is not None:
        parser.error("--piece-limit cannot be combined with --ws")
    if args.ws and args.time_limit_ms is not None:
        parser.error("--time-limit-ms cannot be combined with --ws")

    settings = cfg.load(args.settings)
    bot_args = shlex.split(args.bot_args)

    if args.ws:
        endpoint = websocket_endpoint(
            settings,
            host=args.ws_host,
            port=args.ws_port,
        )
        assert endpoint.port is not None
        ws_pathfinding_options = pathfinding_options(
            settings,
            default_pathfinding=True,
            pathfinding=args.pathfinding,
        )
        server = SuggestionWebSocketServer(
            args.bot,
            bot_args=bot_args,
            settings=settings,
            pathfinding_options=ws_pathfinding_options,
            host=endpoint.host,
            port=endpoint.port,
        )
        try:
            asyncio.run(server.serve_forever())
        except KeyboardInterrupt:
            raise SystemExit(130) from None
        finally:
            server.close()
        return

    total: int = 0
    web_visualizer = None
    if args.web:
        web_endpoint = web_visualizer_endpoint(
            settings,
            host=args.web_host,
            port=args.web_port,
        )
        web_visualizer = WebVisualizer(
            settings,
            host=web_endpoint.host,
            port=web_endpoint.port,
        )
    seed = base_seed(settings, args.seed)
    limits = engine_limits(
        settings,
        piece_limit=args.piece_limit,
        time_limit_ms=args.time_limit_ms,
    )
    try:
        for i in range(args.games):
            print(f"[info] game={i + 1}/{args.games}", file=sys.stderr)
            if args.headless:
                visualizer = HeadlessVisualizer()
            elif web_visualizer is not None:
                visualizer = web_visualizer
            else:
                visualizer = TerminalVisualizer(settings)
            resolved_pathfinding_options = pathfinding_options(
                settings,
                default_pathfinding=visualizer.default_pathfinding,
                pathfinding=args.pathfinding,
            )
            stats = EngineSession(
                args.bot,
                bot_args=bot_args,
                settings=settings,
                visualizer=visualizer,
                random_seed=game_seed(seed, i),
                limits=limits,
                pathfinding_options=resolved_pathfinding_options,
            ).play_game()
            print(
                f"[info] pieces={stats['pieces']} "
                f"elapsed={stats.get('elapsed', 0):.1f}s "
                f"pps={stats.get('pps', 0):.2f}",
                file=sys.stderr,
            )
            total += int(stats["pieces"])
    except KeyboardInterrupt:
        raise SystemExit(130) from None

    if args.games > 1:
        print(f"[info] total_pieces={total} games={args.games}", file=sys.stderr)


if __name__ == "__main__":
    main()
