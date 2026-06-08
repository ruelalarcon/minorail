import argparse
import sys

from engine import EngineSession
import settings as cfg
from visualizer import HeadlessVisualizer, TerminalVisualizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Minorail: TBP bot visualizer")
    parser.add_argument("bot", help="Path to bot executable")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--settings", default="settings.toml")
    args = parser.parse_args()

    settings = cfg.load(args.settings)

    total: int = 0
    try:
        for i in range(args.games):
            print(f"\n=== Game {i + 1} / {args.games} ===", file=sys.stderr)
            visualizer = (
                HeadlessVisualizer()
                if args.no_display
                else TerminalVisualizer(settings)
            )
            stats = EngineSession(args.bot, settings, visualizer).play_game()
            print(
                f"Pieces: {stats['pieces']}  "
                f"Time: {stats.get('elapsed', 0):.1f}s  "
                f"PPS: {stats.get('pps', 0):.2f}",
                file=sys.stderr,
            )
            total += int(stats["pieces"])
    except KeyboardInterrupt:
        raise SystemExit(130) from None

    if args.games > 1:
        print(f"\nTotal: {total} pieces over {args.games} games", file=sys.stderr)


if __name__ == "__main__":
    main()
