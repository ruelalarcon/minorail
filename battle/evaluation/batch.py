from __future__ import annotations

from typing import Any, Callable

from battle.evaluation.collector import EvaluationCollector
from battle.runner.session import Session
from settings import PathSettings, RunLimits, Settings, seed_for_game
from solo.evaluation.batch import _limits, _rules
from suggestion.service import SuggestionService
from visualizers.battle.null import NullVisualizer

ProgressCallback = Callable[[str], None]


def run_evaluation(
    *,
    bot_a_path: str,
    bot_b_path: str,
    bot_a_args: list[str],
    bot_b_args: list[str],
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

    protocol_start = settings.protocol_start()
    bot_cfg = settings.bot()
    service_a = SuggestionService(
        bot_a_path,
        bot_args=bot_a_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )
    service_b = SuggestionService(
        bot_b_path,
        bot_args=bot_b_args,
        piece_stream_limit=protocol_start.piece_stream_limit,
        info_print_topics=settings.bot_info_topics(),
        idle_ms=bot_cfg.idle_ms,
    )
    game_results: list[dict[str, Any]] = []
    try:
        for game_index in range(games):
            game_number = game_index + 1
            seed = seed_for_game(base_seed, game_index)
            collector = EvaluationCollector(include_events=include_events)
            if progress is not None:
                progress(f"[info] battle game={game_number}/{games} seed={seed}")
            session = Session(
                bot_a_path,
                bot_b_path,
                bot_a_args=bot_a_args,
                bot_b_args=bot_b_args,
                settings=settings,
                visualizer=NullVisualizer(),
                service_a=service_a,
                service_b=service_b,
                suggestion_session_id_a="battle-evaluation:A",
                suggestion_session_id_b="battle-evaluation:B",
                session_id=f"battle-eval-{game_number}",
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
                pieces = summary["pieces"]
                total_pieces = pieces["A"] + pieces["B"]
                progress(
                    f"[info] battle game={game_number}/{games} "
                    f"status={summary['status']} winner={summary['winner']} "
                    f"pieces={total_pieces}"
                )
    finally:
        service_a.close()
        service_b.close()

    return {
        "schema": "minorail.eval.battle.v1",
        "label": label,
        "bots": {
            "A": {"path": bot_a_path, "args": bot_a_args},
            "B": {"path": bot_b_path, "args": bot_b_args},
        },
        "rules": _rules(settings),
        "battle": {
            "attack": settings.attack().calculator,
            "garbage": settings.battle_garbage().rules,
        },
        "limits": _limits(limits),
        "summary": _batch_summary(game_results),
        "games": game_results,
    }


def _batch_summary(games: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(games)
    summaries = [game["summary"] for game in games]
    statuses: dict[str, int] = {}
    wins = {"A": 0, "B": 0}
    total_pieces = 0
    total_elapsed_ms = 0
    for summary in summaries:
        statuses[summary["status"]] = statuses.get(summary["status"], 0) + 1
        if summary["winner"] in wins:
            wins[summary["winner"]] += 1
        total_pieces += summary["pieces"]["A"] + summary["pieces"]["B"]
        total_elapsed_ms += summary["elapsed_ms"]
    return {
        "games": count,
        "statuses": statuses,
        "wins": wins,
        "topouts": statuses.get("topout", 0),
        "pieces": _sum_player_metric(summaries, "pieces"),
        "elapsed_ms": total_elapsed_ms,
        "average_pps": (
            total_pieces / (total_elapsed_ms / 1000) if total_elapsed_ms > 0 else 0.0
        ),
        "lines_cleared": _sum_player_metric(summaries, "lines_cleared"),
        "line_clear_placements": _sum_player_metric(summaries, "line_clear_placements"),
        "combo_steps": _sum_player_metric(summaries, "combo_steps"),
        "max_combo": _max_player_metric(summaries, "max_combo"),
        "back_to_back_steps": _sum_player_metric(summaries, "back_to_back_steps"),
        "max_back_to_back": _max_player_metric(summaries, "max_back_to_back"),
        "attack": _sum_player_metric(summaries, "attack"),
        "max_attack": _max_player_metric(summaries, "max_attack"),
        "attack_placements": _sum_player_metric(summaries, "attack_placements"),
        "perfect_clears": _sum_player_metric(summaries, "perfect_clears"),
        "holds": _sum_player_metric(summaries, "holds"),
        "garbage_sent": _sum_player_metric(summaries, "garbage_sent"),
        "garbage_cancelled": _sum_player_metric(summaries, "garbage_cancelled"),
        "garbage_applied": _sum_player_metric(summaries, "garbage_applied"),
        "max_incoming_garbage": _max_player_metric(summaries, "max_incoming_garbage"),
    }


def _sum_player_metric(summaries: list[dict[str, Any]], key: str) -> dict[str, int]:
    return {
        "A": sum(summary[key]["A"] for summary in summaries),
        "B": sum(summary[key]["B"] for summary in summaries),
    }


def _max_player_metric(summaries: list[dict[str, Any]], key: str) -> dict[str, int]:
    return {
        "A": max((summary[key]["A"] for summary in summaries), default=0),
        "B": max((summary[key]["B"] for summary in summaries), default=0),
    }
