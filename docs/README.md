# Minorail

> A local Tetris runner, evaluator, and suggestion service for bots that
> implement the Stacker Bot Protocol (SBP).

Minorail owns the local game truth: board, active piece, upcoming queue, hold,
rules, and sequence number. It starts SBP bot subprocesses, asks for placement
suggestions, filters unusable placements, optionally pathfinds input steps, and
then applies selected placements to local state.

The same core suggestion flow powers:

| Use case | Entry point |
| --- | --- |
| Watch one bot play a local board | `solo play` |
| Run two bots against each other | `battle play` |
| Produce JSON summaries and events | `solo eval`, `battle eval` |
| Serve suggestions to an external client | `solo ws` |

?> Minorail documentation covers Minorail behavior around SBP. For exact SBP
message schemas and bot-side protocol requirements, use the SBP docs:
https://github.com/ruelalarcon/stacker_bot_protocol

## Quick Commands

```bash
python minorail.py solo play "path/to/bot"
python minorail.py solo eval "path/to/bot" --games 100 --json-out solo.json
python minorail.py battle play "path/to/bot-a" "path/to/bot-b"
python minorail.py battle eval "path/to/bot-a" "path/to/bot-b" --games 100 --json-out battle.json
python minorail.py solo ws "path/to/bot"
```

See [Running Minorail](getting-started/running.md) for the full command map.

## Core Concepts

The runner is authoritative for physical state:

| State | Meaning |
| --- | --- |
| `board` | Occupied cells in the local game |
| `active` | Current falling piece |
| `queue` | Upcoming pieces, excluding active |
| `hold` | Current hold piece or none |
| `can_hold` | Whether hold is legal for the current turn |
| `seq` | Sequence number for observed state |

The suggestion service owns derived continuity:

| State | Meaning |
| --- | --- |
| `combo` | Derived combo count |
| `back_to_back` | Derived back-to-back count |
| Previous snapshot | Last physical state seen by the session |
| Previous suggestion | Placement Minorail expects may be applied next |
| Piece stream | Generated piece chronology for SBP `piece_stream` |
| Bot process | Subprocess lifecycle for the session |

Incoming snapshots are always authoritative. When state no longer matches the
expected transition, Minorail reconciles the bot session to the observed state.

## Where To Go

| Topic | Page |
| --- | --- |
| CLI commands and flags | [Running Minorail](getting-started/running.md) |
| One-board local runs | [Solo](modes/solo.md) |
| Two-bot games | [Battle](modes/battle.md) |
| JSON output | [Evaluation](modes/evaluation.md) |
| TOML defaults and overrides | [Settings](reference/settings.md) |
| External suggestion API | [WebSocket API](reference/websocket-api.md) |
| Package boundaries | [Architecture](internals/architecture.md) |
