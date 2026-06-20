from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

from api.websocket import SuggestionWebSocketServer
from battle.evaluation.batch import run_evaluation as run_battle_evaluation
from battle.runner.session import Session as BattleSession
from battle.visualizers.headless import HeadlessVisualizer as BattleHeadlessVisualizer
from battle.visualizers.null import NullVisualizer as BattleNullVisualizer
from battle.visualizers.terminal import TerminalVisualizer as BattleTerminalVisualizer
from settings import Settings, seed_for_game
from solo.evaluation.batch import run_evaluation
from solo.runner.session import LocalGameSession
from solo.visualizers.headless import HeadlessVisualizer as SoloHeadlessVisualizer
from solo.visualizers.null import NullVisualizer as SoloNullVisualizer
from solo.visualizers.terminal import TerminalVisualizer as SoloTerminalVisualizer
from solo.visualizers.web import WebVisualizer
from suggestion.service import SuggestionService


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=30, width=92)

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
        description="Run, evaluate, and serve SBP Tetris bots.",
        formatter_class=_HelpFormatter,
    )
    parser.set_defaults(command=None)
    modes = parser.add_subparsers(dest="mode", metavar="MODE")

    solo = modes.add_parser(
        "solo",
        help="run one bot on a single local board",
        description="Play, evaluate, or serve suggestions for one bot.",
        formatter_class=_HelpFormatter,
    )
    solo_cmds = solo.add_subparsers(dest="command", metavar="COMMAND", required=True)
    _add_solo_play(solo_cmds)
    _add_solo_eval(solo_cmds)
    _add_solo_ws(solo_cmds)

    battle = modes.add_parser(
        "battle",
        help="run two bots against each other",
        description="Play or evaluate a deterministic two-bot battle.",
        formatter_class=_HelpFormatter,
    )
    battle_cmds = battle.add_subparsers(
        dest="command", metavar="COMMAND", required=True
    )
    _add_battle_play(battle_cmds)
    _add_battle_eval(battle_cmds)

    args = parser.parse_args()
    if args.mode is None:
        parser.print_help(sys.stderr)
        raise SystemExit(2)
    args.func(args)


def _add_common(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("settings")
    group.add_argument(
        "--settings",
        metavar="PATH",
        default="settings.toml",
        help="settings TOML file",
    )


def _add_seed_limits(parser: argparse.ArgumentParser) -> None:
    randomizer = parser.add_argument_group("randomizer")
    randomizer.add_argument(
        "--seed",
        metavar="N",
        type=int,
        default=None,
        help="base seed for local piece streams; overrides game.randomizer.seed",
    )
    limits = parser.add_argument_group("limits")
    limits.add_argument(
        "--piece-limit",
        metavar="N",
        type=int,
        default=None,
        help="accepted piece lock limit; overrides game.limits.piece_limit",
    )
    limits.add_argument(
        "--time-limit-ms",
        metavar="MS",
        type=int,
        default=None,
        help="wall-clock time limit in milliseconds; overrides game.limits.time_limit_ms",
    )


def _add_games(parser: argparse.ArgumentParser) -> None:
    games = parser.add_argument_group("games")
    games.add_argument("--games", metavar="N", type=int, default=1, help="games to run")


def _add_pathfinding(parser: argparse.ArgumentParser) -> None:
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


def _add_eval_output(parser: argparse.ArgumentParser) -> None:
    output = parser.add_argument_group("output")
    output.add_argument(
        "--json-out",
        metavar="PATH",
        default="-",
        help="write evaluation JSON to PATH, or '-' for stdout",
    )
    output.add_argument("--label", metavar="TEXT", default=None, help="output label")
    output.add_argument(
        "--no-events",
        action="store_true",
        help="omit per-game event logs and write summaries only",
    )
    output.add_argument(
        "--compact",
        action="store_true",
        help="write compact JSON instead of pretty-printed JSON",
    )
    output.add_argument(
        "--quiet",
        action="store_true",
        help="do not print per-game progress to stderr",
    )


def _add_solo_play(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "play",
        help="run one or more visible solo games",
        description="Run a bot against Minorail's local solo Tetris game.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot", metavar="BOT", help="bot executable or script path")
    _add_common(parser)
    bot = parser.add_argument_group("bot")
    bot.add_argument("--bot-args", metavar="ARGS", default="", help="bot arguments")
    _add_seed_limits(parser)
    _add_games(parser)
    _add_pathfinding(parser)
    display = parser.add_argument_group("visualizer").add_mutually_exclusive_group()
    display.add_argument("--terminal", action="store_true", help="terminal visualizer")
    display.add_argument("--web", action="store_true", help="browser visualizer")
    display.add_argument("--headless", action="store_true", help="progress only")
    web = parser.add_argument_group("web visualizer")
    web.add_argument("--web-host", metavar="HOST", default=None, help="web host")
    web.add_argument(
        "--web-port", metavar="PORT", type=int, default=None, help="web port"
    )
    parser.set_defaults(func=_solo_play)


def _add_solo_eval(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "eval",
        help="run solo batch evaluation",
        description="Run headless solo evaluation and write structured JSON.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot", metavar="BOT", help="bot executable or script path")
    _add_common(parser)
    bot = parser.add_argument_group("bot")
    bot.add_argument("--bot-args", metavar="ARGS", default="", help="bot arguments")
    _add_seed_limits(parser)
    _add_games(parser)
    _add_pathfinding(parser)
    _add_eval_output(parser)
    parser.set_defaults(func=_solo_eval)


def _add_solo_ws(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "ws",
        help="serve the solo websocket suggestion API",
        description="Serve SBP bot suggestions over Minorail's websocket API.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot", metavar="BOT", help="bot executable or script path")
    _add_common(parser)
    bot = parser.add_argument_group("bot")
    bot.add_argument("--bot-args", metavar="ARGS", default="", help="bot arguments")
    _add_pathfinding(parser)
    ws = parser.add_argument_group("websocket api")
    ws.add_argument("--ws-host", metavar="HOST", default=None, help="websocket host")
    ws.add_argument(
        "--ws-port", metavar="PORT", type=int, default=None, help="websocket port"
    )
    parser.set_defaults(func=_solo_ws)


def _add_battle_play(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "play",
        help="run a visible two-bot battle",
        description="Run two SBP bots against each other on local battle boards.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot_a", metavar="BOT_A", help="player A bot path")
    parser.add_argument("bot_b", metavar="BOT_B", help="player B bot path")
    _add_common(parser)
    bot = parser.add_argument_group("bots")
    bot.add_argument(
        "--bot-a-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the player A bot process",
    )
    bot.add_argument(
        "--bot-b-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the player B bot process",
    )
    _add_seed_limits(parser)
    _add_games(parser)
    _add_pathfinding(parser)
    display = parser.add_argument_group("visualizer").add_mutually_exclusive_group()
    display.add_argument("--terminal", action="store_true", help="terminal visualizer")
    display.add_argument("--headless", action="store_true", help="progress only")
    display.add_argument("--null", action="store_true", help="no visual output")
    parser.set_defaults(func=_battle_play)


def _add_battle_eval(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "eval",
        help="run battle batch evaluation",
        description="Run headless two-bot battle evaluation and write structured JSON.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot_a", metavar="BOT_A", help="player A bot path")
    parser.add_argument("bot_b", metavar="BOT_B", help="player B bot path")
    _add_common(parser)
    bot = parser.add_argument_group("bots")
    bot.add_argument(
        "--bot-a-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the player A bot process",
    )
    bot.add_argument(
        "--bot-b-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the player B bot process",
    )
    _add_seed_limits(parser)
    _add_games(parser)
    _add_pathfinding(parser)
    _add_eval_output(parser)
    parser.set_defaults(func=_battle_eval)


def _solo_play(args: argparse.Namespace) -> None:
    settings = Settings.load(args.settings)
    bot_args = _split_args(args.bot_args)
    seed = settings.base_seed(args.seed)
    limits = settings.run_limits(
        piece_limit=args.piece_limit,
        time_limit_ms=args.time_limit_ms,
    )
    protocol_start = settings.protocol_start()
    bot_cfg = settings.bot()
    service = SuggestionService(
        args.bot,
        bot_args=bot_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )
    web_visualizer = None
    if args.web:
        endpoint = settings.web_visualizer_endpoint(
            host=args.web_host,
            port=args.web_port,
        )
        web_visualizer = WebVisualizer(
            settings.visualizer(),
            host=endpoint.host,
            port=endpoint.port,
        )
    total = 0
    try:
        for i in range(args.games):
            print(f"[info] solo game={i + 1}/{args.games}", file=sys.stderr)
            if args.headless:
                visualizer = SoloHeadlessVisualizer()
            elif web_visualizer is not None:
                visualizer = web_visualizer
            else:
                visualizer = SoloTerminalVisualizer(settings.visualizer())
            pathfinding = settings.pathfinding(
                default_pathfinding=visualizer.default_pathfinding,
                pathfinding=args.pathfinding,
            )
            stats = LocalGameSession(
                args.bot,
                bot_args=bot_args,
                settings=settings,
                visualizer=visualizer,
                suggestion_service=service,
                suggestion_session_id="solo-play",
                random_seed=seed_for_game(seed, i),
                limits=limits,
                pathfinding=pathfinding,
            ).play_game()
            total += int(stats["pieces"])
            print(
                f"[info] pieces={stats['pieces']} elapsed={stats['elapsed']:.1f}s "
                f"pps={stats['pps']:.2f}",
                file=sys.stderr,
            )
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    finally:
        service.close()
    if args.games > 1:
        print(f"[info] total_pieces={total} games={args.games}", file=sys.stderr)


def _solo_eval(args: argparse.Namespace) -> None:
    if args.games < 1:
        raise SystemExit("--games must be at least 1")
    settings = Settings.load(args.settings)
    output = run_evaluation(
        bot_path=args.bot,
        bot_args=_split_args(args.bot_args),
        settings=settings,
        games=args.games,
        base_seed=settings.base_seed(args.seed),
        limits=settings.run_limits(
            piece_limit=args.piece_limit,
            time_limit_ms=args.time_limit_ms,
        ),
        pathfinding=settings.pathfinding(
            default_pathfinding=SoloNullVisualizer.default_pathfinding,
            pathfinding=args.pathfinding,
        ),
        label=args.label,
        include_events=not args.no_events,
        progress=None if args.quiet else _print_progress,
    )
    _write_json(output, args.json_out, compact=args.compact)


def _solo_ws(args: argparse.Namespace) -> None:
    settings = Settings.load(args.settings)
    endpoint = settings.websocket_endpoint(host=args.ws_host, port=args.ws_port)
    assert endpoint.port is not None
    server = SuggestionWebSocketServer(
        args.bot,
        bot_args=_split_args(args.bot_args),
        settings=settings,
        pathfinding=settings.pathfinding(
            default_pathfinding=True,
            pathfinding=args.pathfinding,
        ),
        host=endpoint.host,
        port=endpoint.port,
    )
    try:
        asyncio.run(server.serve_forever())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    finally:
        server.close()


def _battle_play(args: argparse.Namespace) -> None:
    if args.games < 1:
        raise SystemExit("--games must be at least 1")
    settings = Settings.load(args.settings)
    if args.headless:
        default_pathfinding = BattleHeadlessVisualizer.default_pathfinding
    elif args.null:
        default_pathfinding = BattleNullVisualizer.default_pathfinding
    else:
        default_pathfinding = BattleTerminalVisualizer.default_pathfinding
    pathfinding = settings.pathfinding(
        default_pathfinding=default_pathfinding,
        pathfinding=args.pathfinding,
    )
    bot_a_args = _split_args(args.bot_a_args)
    bot_b_args = _split_args(args.bot_b_args)
    seed = settings.base_seed(args.seed)
    limits = settings.run_limits(
        piece_limit=args.piece_limit,
        time_limit_ms=args.time_limit_ms,
    )
    protocol_start = settings.protocol_start()
    bot_cfg = settings.bot()
    service_a = SuggestionService(
        args.bot_a,
        bot_args=bot_a_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )
    service_b = SuggestionService(
        args.bot_b,
        bot_args=bot_b_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )
    total = 0
    try:
        for i in range(args.games):
            print(f"[info] battle game={i + 1}/{args.games}", file=sys.stderr)
            if args.headless:
                visualizer = BattleHeadlessVisualizer()
            elif args.null:
                visualizer = BattleNullVisualizer()
            else:
                visualizer = BattleTerminalVisualizer(settings.visualizer())
            session = BattleSession(
                args.bot_a,
                args.bot_b,
                bot_a_args=bot_a_args,
                bot_b_args=bot_b_args,
                settings=settings,
                visualizer=visualizer,
                service_a=service_a,
                service_b=service_b,
                suggestion_session_id_a="battle-play:A",
                suggestion_session_id_b="battle-play:B",
                session_id=f"battle-play-{i + 1}",
                random_seed=seed_for_game(seed, i),
                limits=limits,
                pathfinding=pathfinding,
            )
            stats = session.play_game()
            total += int(stats["total_pieces"])
            print(
                f"[info] battle status={stats['status']} winner={stats['winner']} "
                f"total_pieces={stats['total_pieces']}",
                file=sys.stderr,
            )
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    finally:
        service_a.close()
        service_b.close()
    if args.games > 1:
        print(f"[info] battle total_pieces={total} games={args.games}", file=sys.stderr)


def _battle_eval(args: argparse.Namespace) -> None:
    if args.games < 1:
        raise SystemExit("--games must be at least 1")
    settings = Settings.load(args.settings)
    output = run_battle_evaluation(
        bot_a_path=args.bot_a,
        bot_b_path=args.bot_b,
        bot_a_args=_split_args(args.bot_a_args),
        bot_b_args=_split_args(args.bot_b_args),
        settings=settings,
        games=args.games,
        base_seed=settings.base_seed(args.seed),
        limits=settings.run_limits(
            piece_limit=args.piece_limit,
            time_limit_ms=args.time_limit_ms,
        ),
        pathfinding=settings.pathfinding(
            default_pathfinding=BattleNullVisualizer.default_pathfinding,
            pathfinding=args.pathfinding,
        ),
        label=args.label,
        include_events=not args.no_events,
        progress=None if args.quiet else _print_progress,
    )
    _write_json(output, args.json_out, compact=args.compact)


def _split_args(value: str) -> list[str]:
    return shlex.split(value, posix=os.name != "nt")


def _print_progress(message: str) -> None:
    print(message, file=sys.stderr)


def _write_json(data: dict[str, Any], path: str, *, compact: bool) -> None:
    kwargs: dict[str, Any] = {"separators": (",", ":")} if compact else {"indent": 2}
    if path == "-":
        json.dump(data, sys.stdout, **kwargs)
        print()
        return
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, **kwargs)
        f.write("\n")


if __name__ == "__main__":
    main()
