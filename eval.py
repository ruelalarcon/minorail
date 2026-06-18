from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from evaluation.session import run_evaluation
from runner.seeding import base_seed
import settings as cfg


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
        prog="minorail-eval",
        description="Run batch solo evaluation for an SBP bot.",
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("bot", metavar="BOT", help="bot executable or script path")
    parser.add_argument(
        "--bot-args",
        metavar="ARGS",
        default="",
        help="extra arguments passed to the bot, as one string; "
        'use = when the value starts with a dash, e.g. --bot-args="--config bot.json"',
    )
    parser.add_argument(
        "--games", metavar="N", type=int, default=1, help="games to run"
    )
    parser.add_argument(
        "--settings",
        metavar="PATH",
        default="settings.toml",
        help="settings TOML file",
    )
    parser.add_argument(
        "--seed",
        metavar="N",
        type=int,
        default=None,
        help="per-run base seed for reproducible local piece streams; overrides settings",
    )
    parser.add_argument(
        "--json-out",
        metavar="PATH",
        default="-",
        help="write evaluation JSON to PATH, or '-' for stdout",
    )
    parser.add_argument(
        "--label",
        metavar="TEXT",
        default=None,
        help="optional label included in the output",
    )
    parser.add_argument(
        "--no-events",
        action="store_true",
        help="omit per-game event logs and write summaries only",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="write compact JSON instead of pretty-printed JSON",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="do not print per-game progress to stderr",
    )

    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be at least 1")

    settings = cfg.load(args.settings)
    bot_args = shlex.split(args.bot_args)
    progress = None if args.quiet else _print_progress

    try:
        output = run_evaluation(
            bot_path=args.bot,
            bot_args=bot_args,
            settings=settings,
            games=args.games,
            base_seed=base_seed(settings, args.seed),
            label=args.label,
            include_events=not args.no_events,
            progress=progress,
        )
    except KeyboardInterrupt:
        raise SystemExit(130) from None

    _write_json(output, args.json_out, compact=args.compact)


def _print_progress(message: str) -> None:
    print(message, file=sys.stderr)


def _write_json(data: dict[str, Any], path: str, *, compact: bool) -> None:
    kwargs: dict[str, Any]
    if compact:
        kwargs = {"separators": (",", ":")}
    else:
        kwargs = {"indent": 2}

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
