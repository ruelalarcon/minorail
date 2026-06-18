import argparse
import asyncio
import shlex
import sys

from settings import Settings, seed_for_game
from runner.session import LocalGameSession
from api.websocket import SuggestionWebSocketServer
from suggestion.service import SuggestionService
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
        description="Run a bot against Minorail's local Tetris game.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot", metavar="BOT", help="bot executable or script path")

    settings_group = parser.add_argument_group("settings")
    settings_group.add_argument(
        "--settings",
        metavar="PATH",
        default="settings.toml",
        help="settings TOML file",
    )

    bot_group = parser.add_argument_group("bot")
    bot_group.add_argument(
        "--bot-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the bot, as one string",
    )

    randomizer_group = parser.add_argument_group("randomizer")
    randomizer_group.add_argument(
        "--seed",
        metavar="N",
        type=int,
        default=None,
        help="base seed for local piece streams; overrides game.randomizer.seed",
    )
    limits_group = parser.add_argument_group("limits")
    limits_group.add_argument(
        "--piece-limit",
        metavar="N",
        type=int,
        default=None,
        help="accepted piece lock limit; overrides game.limits.piece_limit",
    )
    limits_group.add_argument(
        "--time-limit-ms",
        metavar="MS",
        type=int,
        default=None,
        help="wall-clock time limit in milliseconds; overrides game.limits.time_limit_ms",
    )

    games_group = parser.add_argument_group("games")
    games_group.add_argument(
        "--games", metavar="N", type=int, default=1, help="games to run"
    )

    path_group = parser.add_argument_group("pathfinding")
    path = path_group.add_mutually_exclusive_group()
    path.add_argument(
        "--pathfind",
        dest="pathfinding",
        action="store_true",
        default=None,
        help="run pathfinding and return input paths; overrides service.path.pathfinding",
    )
    path.add_argument(
        "--no-pathfind",
        dest="pathfinding",
        action="store_false",
        default=None,
        help="skip pathfinding and return placements only; overrides service.path.pathfinding",
    )

    display_group = parser.add_argument_group("visualizer")
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
    web_visualizer_group = parser.add_argument_group("web visualizer")
    web_visualizer_group.add_argument(
        "--web-host",
        metavar="HOST",
        default=None,
        help="host for the web visualizer; overrides visualizer.web.host",
    )
    web_visualizer_group.add_argument(
        "--web-port",
        metavar="PORT",
        type=int,
        default=None,
        help="port for the web visualizer; overrides visualizer.web.port",
    )

    api_group = parser.add_argument_group("websocket api")
    api_group.add_argument(
        "--ws",
        action="store_true",
        help="serve suggestions over a websocket API",
    )
    api_group.add_argument(
        "--ws-host",
        metavar="HOST",
        default=None,
        help="host for the websocket API; overrides api.websocket.host",
    )
    api_group.add_argument(
        "--ws-port",
        metavar="PORT",
        type=int,
        default=None,
        help="port for the websocket API; overrides api.websocket.port",
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

    settings = Settings.load(args.settings)
    bot_args = shlex.split(args.bot_args)

    if args.ws:
        endpoint = settings.websocket_endpoint(
            host=args.ws_host,
            port=args.ws_port,
        )
        assert endpoint.port is not None
        pathfinding = settings.pathfinding(
            default_pathfinding=True,
            pathfinding=args.pathfinding,
        )
        server = SuggestionWebSocketServer(
            args.bot,
            bot_args=bot_args,
            settings=settings,
            pathfinding=pathfinding,
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
        web_endpoint = settings.web_visualizer_endpoint(
            host=args.web_host,
            port=args.web_port,
        )
        web_visualizer = WebVisualizer(
            settings.visualizer(),
            host=web_endpoint.host,
            port=web_endpoint.port,
        )
    seed = settings.base_seed(args.seed)
    limits = settings.run_limits(
        piece_limit=args.piece_limit,
        time_limit_ms=args.time_limit_ms,
    )
    protocol_start = settings.protocol_start()
    bot_cfg = settings.bot()
    suggestion_service = SuggestionService(
        args.bot,
        bot_args=bot_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )
    try:
        for i in range(args.games):
            print(f"[info] game={i + 1}/{args.games}", file=sys.stderr)
            if args.headless:
                visualizer = HeadlessVisualizer()
            elif web_visualizer is not None:
                visualizer = web_visualizer
            else:
                visualizer = TerminalVisualizer(settings.visualizer())
            pathfinding = settings.pathfinding(
                default_pathfinding=visualizer.default_pathfinding,
                pathfinding=args.pathfinding,
            )
            stats = LocalGameSession(
                args.bot,
                bot_args=bot_args,
                settings=settings,
                visualizer=visualizer,
                suggestion_service=suggestion_service,
                suggestion_session_id="local-run",
                random_seed=seed_for_game(seed, i),
                limits=limits,
                pathfinding=pathfinding,
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
    finally:
        suggestion_service.close()

    if args.games > 1:
        print(f"[info] total_pieces={total} games={args.games}", file=sys.stderr)


if __name__ == "__main__":
    main()
