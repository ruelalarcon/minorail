# Evaluation

Use evaluation commands when you want machine-readable output instead of a
visualized run.

```bash
python minorail.py solo eval "path/to/sbp-bot" --games 100 --seed 123 --json-out results.json
python minorail.py battle eval "path/to/bot-a" "path/to/bot-b" --games 100 --seed 123 --json-out battle.json
```

Evaluation uses Minorail's local game, settings, SBP bot launcher, and seed
handling. It runs with a null visualizer and writes structured JSON for
analysis or ML training.

---

## Solo Evaluation

Solo output uses schema `minorail.eval.v1`:

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

Per-game summaries include generic run rollups: status, pieces, elapsed time,
pps, lines cleared, line-clear placements, combo steps, max combo,
back-to-back steps, max back-to-back, perfect clears, and holds.

Each solo `piece_locked` event records placement, hold use, line clear facts,
combo and back-to-back before/after values, stack height, and occupied cells.

---

## Battle Evaluation

Battle output uses schema `minorail.battle.eval.v1`:

```json
{
  "schema": "minorail.battle.eval.v1",
  "bots": {
    "A": {"path": "path/to/bot-a", "args": []},
    "B": {"path": "path/to/bot-b", "args": []}
  },
  "battle": {
    "attack": "generic",
    "garbage": "generic"
  },
  "summary": {},
  "games": []
}
```

Battle evaluation keeps two bot processes alive across a multi-game batch and
sends per-player stop-game semantics at each game boundary.

Battle `piece_locked` events include the same core solo lock facts plus:

| Field | Meaning |
| --- | --- |
| `player` | Player id, currently `A` or `B`. |
| `attack` | Total attack produced by the lock. |
| `attack_breakdown` | Components such as line clear, combo, back-to-back, and perfect clear. |
| `incoming_garbage_before` | Pending garbage before cancellation. |
| `garbage_cancelled` | Incoming garbage cancelled by this attack. |
| `garbage_sent` | Garbage queued for the opponent. |
| `incoming_garbage_after` | Pending garbage remaining after cancellation and any rise. |

`garbage_applied` events are emitted only when garbage is physically inserted
into a board. Normal 1v1 top-out is represented by `game_ended` with
`status: "topout"`, `winner`, and `loser`.

---

## Generic Battle Defaults

The built-in battle rules are Minorail generic defaults. They are structurally
useful for local experiments and are not documented as TETR.IO or PPT behavior.

Generic attack:

| Clear | Attack |
| --- | --- |
| Single | 0 |
| Double | 1 |
| Triple | 2 |
| Quad | 4 |
| T-spin single | 2 |
| T-spin double | 4 |
| T-spin triple | 6 |
| Perfect clear bonus | 10 |

The generic calculator also adds an explicit combo bonus of `1` per combo step
after the first combo value and a static back-to-back bonus of `1` when
`back_to_back_after >= 2`.

Generic garbage uses full cancellation/blocking, applies pending garbage on
non-line-clearing locks, caps garbage rise at 8 lines per lock, and generates
holes deterministically from the battle seed. It does not implement passthrough.

---

## Shared Flags

| Category | Flags | Behavior |
| --- | --- | --- |
| `settings` | `--settings PATH` | Settings TOML file. |
| `bot` / `bots` | `--bot-args`, `--bot-a-args`, `--bot-b-args` | Extra arguments passed to bot processes. |
| `randomizer` | `--seed N` | Base seed for local piece streams; overrides `game.randomizer.seed`. |
| `limits` | `--piece-limit N` | Stops each game after this many accepted locks. |
| `limits` | `--time-limit-ms MS` | Stops each game after this many milliseconds. |
| `games` | `--games N` | Number of games to evaluate. |
| `pathfinding` | `--pathfind`, `--no-pathfind` | Override pathfinding for one invocation. |
| `output` | `--json-out PATH` | Writes evaluation JSON to a file. Use `-` for stdout. |
| `output` | `--label TEXT` | Adds an experiment or candidate label to the output. |
| `output` | `--no-events` | Omits per-game event logs and writes summaries only. |
| `output` | `--compact` | Writes compact JSON. |
| `output` | `--quiet` | Disables progress logs on stderr. |
