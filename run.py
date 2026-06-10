import argparse
import asyncio
import shlex
import sys

from runner.engine_session import EngineSession
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
        default="127.0.0.1",
        help="host for the web visualizer",
    )
    display_group.add_argument(
        "--web-port",
        metavar="PORT",
        type=int,
        default=None,
        help="port for the web visualizer (default: auto)",
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
        default="127.0.0.1",
        help="host for the websocket API",
    )
    api_group.add_argument(
        "--ws-port",
        metavar="PORT",
        type=int,
        default=8444,
        help="port for the websocket API",
    )
    args = parser.parse_args()
    if args.ws and (args.terminal or args.web or args.headless):
        parser.error("--ws cannot be combined with visualization modes")

    settings = cfg.load(args.settings)
    bot_args = shlex.split(args.bot_args)

    if args.ws:
        server = SuggestionWebSocketServer(
            args.bot,
            bot_args=bot_args,
            settings=settings,
            host=args.ws_host,
            port=args.ws_port,
        )
        try:
            asyncio.run(server.serve_forever())
        except KeyboardInterrupt:
            raise SystemExit(130) from None
        finally:
            server.close()
        return

    total: int = 0
    web_visualizer = (
        WebVisualizer(
            settings,
            host=args.web_host,
            port=args.web_port,
        )
        if args.web
        else None
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
            stats = EngineSession(
                args.bot,
                bot_args=bot_args,
                settings=settings,
                visualizer=visualizer,
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
