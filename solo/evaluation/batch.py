from __future__ import annotations

import time
from typing import Any, Callable

from settings import PathSettings, RunLimits, Settings, seed_for_game
from solo.evaluation.collector import EvaluationCollector
from solo.runner.session import LocalGameSession
from suggestion.service import SuggestionService
from tetris.model.rules import Rules
from visualizers.solo.null import NullVisualizer

ProgressCallback = Callable[[str], None]


def run_evaluation(
    *,
    bot_path: str,
    bot_args: list[str],
    settings: Settings,
    games: int,
    base_seed: int | None,
    limits: RunLimits,
    pathfinding: PathSettings,
    label: str | None = None,
    include_events: bool = True,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    if games < 1:
        raise ValueError("games must be at least 1")

    started_at = time.time()
    game_results: list[dict[str, Any]] = []
    protocol_start = settings.protocol_start()
    bot_cfg = settings.bot()
    suggestion_service = SuggestionService(
        bot_path,
        bot_args=bot_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )

    try:
        for game_index in range(games):
            game_number = game_index + 1
            seed = seed_for_game(base_seed, game_index)
            session_id = f"eval-{game_number}"
            collector = EvaluationCollector(include_events=include_events)

            if progress is not None:
                progress(f"[info] game={game_number}/{games} seed={seed}")

            session = LocalGameSession(
                bot_path,
                bot_args=bot_args,
                settings=settings,
                visualizer=NullVisualizer(),
                session_id=session_id,
                suggestion_session_id="evaluation",
                suggestion_service=suggestion_service,
                random_seed=seed,
                limits=limits,
                pathfinding=pathfinding,
                observers=[collector],
            )
            session.play_game()
            result = collector.result(game=game_index)
            game_results.append(result)

            if progress is not None:
                summary = result["summary"]
                progress(
                    f"[info] game={game_number}/{games} "
                    f"status={summary['status']} "
                    f"pieces={summary['pieces']} "
                    f"elapsed_ms={summary['elapsed_ms']}"
                )
    finally:
        suggestion_service.close()

    elapsed = time.time() - started_at
    return {
        "schema": "minorail.eval.solo.v1",
        "label": label,
        "bot": {
            "path": bot_path,
            "args": bot_args,
        },
        "rules": _rules(settings),
        "limits": _limits(limits),
        "summary": _batch_summary(game_results),
        "elapsed_ms": round(elapsed * 1000),
        "games": game_results,
    }


def _rules(settings: Settings) -> dict[str, Any]:
    rules = Rules.from_values(settings.rules_values())
    return {
        "randomizer": rules.randomizer,
        "kickset": rules.kickset,
        "rot180": rules.rot180,
        "sonic_drop": rules.sonic_drop,
        "allspin_b2b": rules.allspin_b2b,
        "allclear_b2b": rules.allclear_b2b,
        "spawn_x": rules.spawn_x,
        "spawn_y": rules.spawn_y,
    }


def _limits(limits: RunLimits) -> dict[str, Any]:
    return {
        "piece_limit": limits.piece_limit,
        "time_limit_ms": limits.time_limit_ms,
    }


def _batch_summary(games: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(games)
    summaries = [game["summary"] for game in games]
    total_pieces = sum(summary["pieces"] for summary in summaries)
    total_elapsed_ms = sum(summary["elapsed_ms"] for summary in summaries)
    statuses: dict[str, int] = {}
    for summary in summaries:
        status = summary["status"]
        statuses[status] = statuses.get(status, 0) + 1

    return {
        "games": count,
        "statuses": statuses,
        "topouts": statuses.get("topout", 0),
        "total_pieces": total_pieces,
        "average_pieces": total_pieces / count if count else 0.0,
        "min_pieces": min((summary["pieces"] for summary in summaries), default=0),
        "max_pieces": max((summary["pieces"] for summary in summaries), default=0),
        "total_elapsed_ms": total_elapsed_ms,
        "average_elapsed_ms": total_elapsed_ms / count if count else 0.0,
        "average_pps": (
            total_pieces / (total_elapsed_ms / 1000) if total_elapsed_ms > 0 else 0.0
        ),
        "lines_cleared": sum(summary["lines_cleared"] for summary in summaries),
        "line_clear_placements": sum(
            summary["line_clear_placements"] for summary in summaries
        ),
        "combo_steps": sum(summary["combo_steps"] for summary in summaries),
        "max_combo": max((summary["max_combo"] for summary in summaries), default=0),
        "back_to_back_steps": sum(
            summary["back_to_back_steps"] for summary in summaries
        ),
        "max_back_to_back": max(
            (summary["max_back_to_back"] for summary in summaries),
            default=0,
        ),
        "perfect_clears": sum(summary["perfect_clears"] for summary in summaries),
        "holds": sum(summary["holds"] for summary in summaries),
    }
