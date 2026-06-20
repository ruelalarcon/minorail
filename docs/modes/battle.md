# Battle

Battle mode runs two SBP bots against each other on two local boards.

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b"
```

Each player is a local game board. Minorail asks both bots for suggestions,
locks accepted placements, calculates attack, exchanges garbage, and ends the
game on top-out or configured limits.

## Commands

| Task | Command |
| --- | --- |
| Terminal battle | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b"` |
| Headless battle | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --headless` |
| Null visualizer | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --null` |
| Multiple games | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --games 20` |
| Battle evaluation | `python minorail.py battle eval "path/to/bot-a" "path/to/bot-b" --games 100 --json-out battle.json` |

Battle bot arguments are per process:

```bash
python minorail.py battle play "bot-a" "bot-b" --bot-a-args="--profile a" --bot-b-args="--profile b"
```

## Runner Flow

```text
battle.runner.session.Session
  -> Player A LocalGame
  -> Player B LocalGame
  -> SuggestionService sessions
  -> attack calculator
  -> garbage rules
  -> battle visualizer
```

Battle reuses solo `LocalGame` for each board, but battle orchestration owns
player turns, attack calculation, pending garbage, garbage insertion, and
winner/loser state.

## Process Reuse

Multi-game battle runs reuse the same two bot processes across the batch when
possible. Minorail keeps stable suggestion session ids for player A and player B
and sends per-player stop-game semantics at each game boundary.

## Generic Attack

The built-in calculator is `generic`. It is Minorail's deterministic default,
not a TETR.IO or PPT ruleset.

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

It also adds `1` attack per combo step after the first combo value and a static
back-to-back bonus of `1` when `back_to_back_after >= 2`.

## Generic Garbage

The built-in garbage rules are also `generic`:

| Behavior | Value |
| --- | --- |
| Cancellation | Full attack-vs-incoming cancellation |
| Passthrough | None |
| Rise timing | Non-line-clearing locks |
| Rise cap | 8 lines per lock |
| Holes | Deterministic from the battle seed |

`garbage_applied` events mean garbage was physically inserted into a board.

## Limits

`--piece-limit N` and `--time-limit-ms MS` are per battle game. In battle play,
the piece limit counts total accepted locks across both players.

## Related Pages

* [Evaluation](evaluation.md)
* [Settings](../reference/settings.md#battle-settings)
* [Visualizers](../internals/visualizers.md)
