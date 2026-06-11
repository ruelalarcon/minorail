# Minorail

> A local Tetris engine and bot runner for bots that implement the Stacker Bot Protocol (SBP).

---

In practical terms, Minorail:

* owns the board, active piece, queue, hold state, and sequence number
* starts an SBP bot subprocess
* sends rules and start snapshots to the bot
* asks the bot for placement suggestions
* filters unusable placements
* can calculate an input path to the selected placement
* applies the selected placement to local game state
* can run with a terminal, web, or headless visualizer
* can expose suggestions through a websocket API

?> For protocol-level documentation, message schemas, and bot implementation
details, use the SBP docs:

https://github.com/ruelalarcon/stacker_bot_protocol

These docs focus on Minorail behavior around SBP: how Minorail starts bots,
which settings affect the `rules` and `start` messages, how sessions are kept
in sync, and how websocket callers interact with the suggestion service.

## SBP In Minorail

Minorail uses SBP as the bot process protocol. It starts a bot subprocess,
waits for registration, validates configured rules against reported
capabilities, sends `rules` when needed, sends `start` from the current
snapshot, then asks for suggestions.

| Minorail event | SBP interaction |
| --- | --- |
| Bot process starts | Minorail waits for `register` |
| Rules are new or changed | Minorail sends `rules` and waits for `ready` |
| Session starts or resyncs | Minorail sends `start` |
| Minorail needs a placement | Minorail sends `suggest` |
| Snapshot advances as expected | Minorail sends `play` and any `new_piece` messages |
| Session resets | Minorail sends `stop`, then starts again from a new snapshot |
| Process closes | Minorail sends `quit` |

!> Minorail docs intentionally do not redefine SBP message schemas. If you are
writing a bot, read the SBP docs for the exact protocol contract.

## Main Use Cases

Use Minorail when you want to:

* run an SBP bot against a local Tetris engine
* watch bot decisions in a visualizer
* batch run games from the command line
* serve an SBP backed suggestion service over websockets
* test how a bot handles rule settings, hold, queues, piece streams, and resyncs

## What Minorail Owns

The local engine is the authority for physical game state:

| State | Meaning |
| --- | --- |
| `board` | Occupied cells in the local engine |
| `active` | Current falling piece |
| `queue` | Upcoming pieces, excluding active |
| `hold` | Current hold piece or none |
| `can_hold` | Whether hold is legal for the current turn |
| `seq` | Sequence number for observed state |

The suggestion service tracks derived state needed to keep the bot session
coherent:

| State | Meaning |
| --- | --- |
| `combo` | Derived combo count |
| `back_to_back` | Derived back to back count |
| Previous snapshot | Last physical state seen by the session |
| Previous suggestion | Placement Minorail expects may be applied next |
| Piece stream | Generated piece chronology for SBP `piece_stream` |
| Bot process | Subprocess lifecycle for the session |

The incoming snapshot is always authoritative. If the state no longer matches
what Minorail expected, Minorail resyncs instead of assuming the bot session is
still correct.

## Where To Start

Read these first:

* [Running Minorail](running.md)
* [Settings](settings.md)
* [WebSocket API](websocket-api.md)
* [Sessions And Resyncs](sessions-and-resyncs.md)
