# Evaluation

Use `eval.py` when you want machine-readable solo evaluation instead of a
visualized game run.

```bash
python eval.py "path/to/sbp-bot" --games 100 --seed 123 --json-out results.json
```

Evaluation still uses Minorail's local engine, settings, SBP bot launcher, and
seed handling. The difference is that it runs with a null visualizer and writes
structured JSON for analysis.

---

## Command

```bash
python eval.py "path/to/sbp-bot" --games 100 --json-out results.json
```

Useful options:

| Option | Behavior |
| --- | --- |
| `--games N` | Number of games to evaluate. |
| `--seed N` | Per-run base seed for local piece streams. Overrides `engine.randomizer.seed`. |
| `--settings PATH` | Settings TOML file. |
| `--bot-args ARGS` | Extra arguments passed to the bot process. |
| `--piece-limit N` | Stops each game after this many accepted piece locks. Overrides `engine.limits.piece_limit`. |
| `--time-limit-ms MS` | Stops each game after this many milliseconds. Overrides `engine.limits.time_limit_ms`. |
| `--pathfind` | Runs pathfinding during evaluation. By default evaluation skips pathfinding. |
| `--no-pathfind` | Skips pathfinding during evaluation, overriding settings. |
| `--json-out PATH` | Writes evaluation JSON to a file. Use `-` for stdout. |
| `--label TEXT` | Adds an experiment or candidate label to the output. |
| `--no-events` | Omits per-game event logs and writes summaries only. |
| `--compact` | Writes compact JSON. |
| `--quiet` | Disables progress logs on stderr. |

When multiple games run with a seed, each game uses `seed + game_index`, where
`game_index` starts at `0`.

---

## Output

The output uses schema `minorail.eval.v1`:

```json
{
  "schema": "minorail.eval.v1",
  "label": "candidate-001",
  "bot": {
    "path": "path/to/sbp-bot",
    "args": ["--config", "candidate.json"]
  },
  "rules": {},
  "limits": {
    "piece_limit": 1000,
    "time_limit_ms": 30000
  },
  "summary": {},
  "elapsed_ms": 1234,
  "games": []
}
```

The top-level `summary` contains batch rollups across every game. Each item in
`games` contains the game seed, a per-game `summary`, and per-game `events`
unless `--no-events` is used.

---

## Summaries

Per-game summaries include generic engine rollups:

| Field | Meaning |
| --- | --- |
| `status` | Terminal status such as `topout`, `no_suggestion`, or `apply_move_rejected`. |
| `pieces` | Accepted piece locks. |
| `elapsed_ms` | Game wall-clock duration. |
| `pps` | Accepted piece locks per second. |
| `lines_cleared` | Total cleared lines. |
| `line_clear_placements` | Locks that cleared at least one line. |
| `combo_steps` | Locks where `combo_after > combo_before`. |
| `combo_total` | Sum of `combo_after` over accepted locks. |
| `max_combo` | Maximum `combo_after`. |
| `back_to_back_steps` | Locks where `back_to_back_after > back_to_back_before`. |
| `back_to_back_total` | Sum of `back_to_back_after` over accepted locks. |
| `max_back_to_back` | Maximum `back_to_back_after`. |
| `perfect_clears` | Locks that produced a perfect clear. |
| `holds` | Accepted locks that used hold. |

The batch summary includes the same aggregate counters plus batch-level fields
such as `games`, `statuses`, `topouts`, `total_pieces`, `average_pieces`,
`min_pieces`, `max_pieces`, `total_elapsed_ms`, `average_elapsed_ms`, and
`average_pps`.

Terminal statuses:

| Status | Meaning |
| --- | --- |
| `topout` | The board reached above the visible 20-row playfield after a lock. |
| `piece_limit` | The configured accepted piece lock limit was reached. |
| `time_limit` | The configured wall-clock time limit was reached. |
| `no_suggestion` | The bot did not return a usable suggestion. |
| `invalid_move` | The selected placement could not be matched to the current active, hold, or empty-hold swap state. |
| `apply_move_rejected` | The selected placement failed local legality checks during application. |
| `bot_startup_failed` | The bot process failed during startup or capability negotiation. |
| `interrupted` | The engine was interrupted while the game was running. |

---

## Events

Each `piece_locked` event records the accepted placement and engine facts after
the lock:

```json
{
  "type": "piece_locked",
  "piece_index": 42,
  "placement": {
    "piece": "T",
    "orientation": "south",
    "x": 4,
    "y": 1,
    "spin": "full"
  },
  "hold_used": false,
  "lines_cleared": 2,
  "perfect_clear": false,
  "combo_before": 2,
  "combo_after": 3,
  "back_to_back_before": 5,
  "back_to_back_after": 6,
  "stack_height": 17,
  "occupied_cells": 86
}
```

Each game also ends with a `game_ended` event containing the terminal status and
final board facts. Optimizers can compute custom metrics, such as attack per
piece, from these event facts without Minorail owning an attack table.
