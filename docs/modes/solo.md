# Solo

Solo mode runs one local Tetris board against one SBP bot.

```bash
python minorail.py solo play "path/to/bot"
```

Minorail owns the physical game state, asks the bot for placements, applies the
first usable placement, and advances the game until top-out, a configured limit,
or a run error.

## Commands

| Task | Command |
| --- | --- |
| Terminal visualizer | `python minorail.py solo play "path/to/bot"` |
| Browser visualizer | `python minorail.py solo play "path/to/bot" --web` |
| Headless progress logs | `python minorail.py solo play "path/to/bot" --headless` |
| Multiple games | `python minorail.py solo play "path/to/bot" --games 20` |
| JSON evaluation | `python minorail.py solo eval "path/to/bot" --games 100 --json-out results.json` |
| Websocket suggestion API | `python minorail.py solo ws "path/to/bot"` |

## State Flow

Each solo turn follows the same authority boundary:

```text
LocalGame
  -> ObservedSnapshot
  -> SuggestionService
  -> BotSession
  -> SBP bot process
  -> selected placement
  -> GameState.apply_move()
```

`LocalGame` owns board mutation, queue refill, hold state, and snapshots. The
visualizer observes state and may request edits through runner controls, but it
does not mutate `GameState.board` directly.

## Placement Selection

Bots may return multiple placements. Minorail selects the first placement that:

* fits the current board
* can be explained by active-piece or hold semantics
* can be applied by `GameState.apply_move()`

If no usable placement is returned before the timeout, the suggestion status is
`no_suggestion`.

## Multi-Game Runs

`--games N` runs multiple games with one bot process when possible. At each game
boundary, Minorail sends SBP `stop`, starts the next game from a fresh snapshot,
and sends `quit` only after the whole run ends.

When a base seed is configured or passed with `--seed`, game `i` uses
`seed + i`, where `i` starts at `0`.

## Limits

`--piece-limit N` and `--time-limit-ms MS` are per game. They override
`[game.limits]` for that invocation.

```bash
python minorail.py solo play "path/to/bot" --piece-limit 1000 --time-limit-ms 30000
```

## Pathfinding

Terminal and web solo visualizers request paths by default so they can animate
movement. Headless, null, and evaluation consumers do not.

Use `--pathfind` or `--no-pathfind` to override both the consumer default and
`[service.path].pathfinding` for one invocation.

## Related Pages

* [Gameplay Behavior](../reference/gameplay-behavior.md)
* [Evaluation](evaluation.md)
* [Session Reconciliation](../internals/session-reconciliation.md)
