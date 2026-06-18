# Development And Extension

Most users do not need this page. It is for changing Minorail itself.

## Checks

Run tests:

```bash
python -m pytest
```

Run lint and type checks:

```bash
./lint.sh
```

On Windows PowerShell:

```powershell
.\lint.ps1
```

## Package Map

Minorail is organized by responsibility:

```text
tetris/       Tetris model, rules, kicks, movement, randomizers, state
contracts/    shared request, result, and snapshot dataclasses
api/          external API transports
sbp/          SBP parsing, serialization, capabilities, and message shape
bots/         bot subprocess transport and SBP session lifecycle
suggestion/   session continuity, derived state, and move selection
runner/       local game sessions, run observers, and visualizer controls
evaluation/   batch evaluation runner and collector
visualizers/  terminal, web, headless, and null renderers
```

Keep protocol details out of Tetris domain modules. Keep gameplay mutation out
of visualizers.

## Adding A Kickset

Kick tables live in `tetris/kicks/`.

A kickset should define explicit rotation transitions. Unsupported transitions
should be absent rather than special cased in move generation.

After adding the table:

* register it in the kick registry
* add tests for expected rotations
* document the new `protocol.rules.kickset` value
* make sure SBP bot capability validation can refer to the same name

## Adding A Randomizer

Randomizers live in `tetris/randomizer/`.

After adding one:

* implement the randomizer interface
* register it in the randomizer factory
* add tests for generation behavior
* document the new `protocol.rules.randomizer` value

## Adding A Visualizer

Visualizers are observers and controllers.

A visualizer should implement the runner visualizer callbacks and receive
`GameControls` from the runner.

It can request edits through controls, but it should not mutate
`GameState.board` directly.

## Changing Hold Or Move Selection

Keep these aligned:

* `GameState.apply_move()`
* `suggestion.move_selection.pick_move()`

Both must agree on when active, hold, and empty hold swap placements are legal.

## Changing SBP Behavior

SBP wire format handling belongs in `sbp/` and the bot adapter.

Do not duplicate SBP protocol documentation in Minorail docs or code comments.
Link to the SBP docs when the exact protocol definition is needed.
