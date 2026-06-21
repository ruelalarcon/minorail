# Architecture

Minorail is split around ownership boundaries: Tetris rules and mutation,
SBP transport, suggestion continuity, runner orchestration, and presentation.

## Package Map

```text
tetris/       Tetris domain model, pieces, kicks, movegen, randomizers, game state
contracts/    shared request, result, and snapshot dataclasses
api/          external API transports
sbp/          SBP parsing, serialization, capabilities, and message shape
suggestion/   session continuity, derived state, and move selection
bots/         bot subprocess transport and SBP session lifecycle
tetris/attack/ attack calculators derived from locked moves
solo/         one-board runner and evaluation
battle/       two-board runner, evaluation, and garbage exchange/application
visualizers/  solo and battle renderers plus shared visualizer infrastructure
frostetra/    Rust SBP bot that can be launched by Minorail
tetrio_client/ TETR.IO integration client and patching notes
minocontroller/ input controller support package
stacker_bot_protocol/ vendored SBP documentation/specification
docs/         documentation site content
```

## Ownership

Physical truth belongs to the client or runner:

| State | Owner |
| --- | --- |
| Board cells | `solo.runner.local_game.LocalGame` / `tetris.game.GameState` |
| Active piece | Local game state |
| Upcoming queue | Local game state |
| Hold and can-hold | Local game state |
| Sequence number | Runner or external websocket client |

Derived truth belongs to `suggestion/`:

| State | Owner |
| --- | --- |
| Combo and back-to-back continuity | `suggestion.derived_state` |
| Previous observed snapshot | `suggestion.session` |
| Previous selected suggestion | `suggestion.session` |
| Piece stream alignment | `suggestion.piece_stream_tracker` |
| Bot session continuity | `bots.session` through `SuggestionService` |

Incoming snapshots remain authoritative. The suggestion layer reconciles bot
continuity around snapshots; it does not override observed game state.

## Solo Flow

```text
solo.runner.session.LocalGameSession
  -> solo.runner.local_game.LocalGame
  -> contracts.ObservedSnapshot
  -> suggestion.service.SuggestionService
  -> suggestion.session.SuggestionContinuity
  -> bots.session.BotSession
  -> bots.process.BotProcess
  -> sbp messages
```

## Battle Flow

```text
battle.runner.session.Session
  -> battle.runner.player.Player
  -> solo.runner.local_game.LocalGame
  -> suggestion.service.SuggestionService
  -> tetris.attack.AttackCalculator
  -> battle.garbage.GarbageRules
  -> battle visualizer/evaluation observer
```

Battle composes two solo local boards. It does not make visualizers responsible
for attack, garbage, or gameplay mutation.

## Protocol Boundary

`sbp/` owns JSON-line message parsing and serialization. `bots/` owns process
lifecycle and SBP session orchestration. Tetris domain modules should not know
about protocol message shapes.

SBP message schemas are intentionally not duplicated in these docs. Use the SBP
documentation when the exact wire contract is needed.

## Visualizer Boundary

Visualizers are observers and controllers. They may receive controls from a
runner and request edits through those controls, but they should not mutate
`GameState.board` directly.

Solo and battle visualizers use separate protocols so two-player presentation
does not leak into the solo runner API.
