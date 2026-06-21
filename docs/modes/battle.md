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
| Browser battle | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --web` |
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

## Attack Calculators

The default calculator is `tetrio_s2`. Battle attack calculators convert
already-produced `AppliedMove` facts into total attack; gameplay state such as
combo, back-to-back continuation, all-spins, and perfect-clears is owned by the
local game rules before the calculator runs.

Built-in calculators:

| Name | Behavior |
| --- | --- |
| `tetrio_s2` | Current TETR.IO-style Tetra League attack: multiplier combo, repeated back-to-back bonus, back-to-back surge, 5-line perfect-clear bonus, and S2 perfect-clear special bonus. |
| `tetrio_s1` | TETR.IO season 1 style attack: multiplier combo, logarithmic back-to-back chaining, and 10-line perfect-clear bonus. |
| `ppt` | Puyo Puyo Tetris-style attack gauge based on public community notes: adjusted T-Spin Double, T-Spin Triple, perfect-clear, back-to-back, and combo values. |
| `classic_guideline` | T-spin/line-clear attack with the classic fixed additive combo table. |
| `modern_guideline` | T-spin/line-clear attack with the modern fixed additive combo table. |

Minorail combo and back-to-back counters start at `1` on the first clear in a
chain. TETR.IO and guideline attack formulas use the displayed/derived count,
so these calculators subtract one before applying combo and back-to-back attack formulas.

## Garbage Rules

The built-in garbage rules are `modern`, `ppt`, and `tetrio`. The default is
`modern`:

| Behavior | Value |
| --- | --- |
| Cancellation | Full attack-vs-incoming cancellation |
| Passthrough | None |
| Rise timing | Non-line-clearing locks |
| Rise cap | 8 lines per lock |
| `tetrio` holes | One hole per incoming garbage entry, rerolled between entries |
| `ppt` holes | Puyo Puyo Tetris-style messier holes: 30% chance to change after each line, 90% chance to change after each incoming garbage entry |
| `modern` holes | Tetris Effect: Connected Zone Battle-inspired phases: clean entry columns at game start, slightly messier after about 50 locks, very messy after about 150 locks |

The `ppt` rule is based on public community reverse-engineering, not an
official Sega or Tetris Guideline specification. The behavior note comes from
FOUR.lol's Puyo Puyo Tetris garbage notes, which credit Okey_Dokey for the
information: <https://four.lol/mid-game/puyo-puyo-tetris>.

The `ppt` attack calculator is based on FOUR.lol's Puyo Puyo Tetris attack
gauge notes from the same page.

The `modern` rule is based on TetrisWiki's Zone Battle notes for Tetris
Effect: Connected: garbage hole alignment has three score phases, starting as
clean random columns, becoming slightly more random at 20,000 points, and very
random at 60,000 points:
<https://tetris.wiki/Tetris_Effect#Zone_Battle>. Minorail does not track
Tetris Effect score or Zone state in garbage rules, so it approximates those
phase changes with per-player lock counts. The phase state is stored in the
per-game garbage queue and resets between games.

`garbage_applied` events mean garbage was physically inserted into a board.

## Limits

`--piece-limit N` and `--time-limit-ms MS` are per battle game. In battle play,
the piece limit counts total accepted locks across both players.

## Related Pages

* [Evaluation](evaluation.md)
* [Settings](../reference/settings.md#battle-settings)
* [Visualizers](../internals/visualizers.md)
