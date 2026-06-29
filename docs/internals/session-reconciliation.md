# Session Reconciliation

Minorail sessions preserve bot continuity across suggestion requests.

?> Use sessions when you want the bot to keep its internal state between
suggestions. Use separate `session_id` values for independent games.

This matters because an SBP bot session has internal state. Minorail classifies
each authoritative snapshot transition, then reconciles the bot session with
the least disruptive valid SBP operations. If continuity can be preserved, it
sends operations such as `advance`, `new_piece`, or `board`. If continuity cannot
be preserved, it resets the bot from the authoritative snapshot.

---

## Session Ids

| Context | Session behavior |
| --- | --- |
| Local game runner | Uses a fixed session id for the game. |
| Websocket request without `session_id` | Uses a default session for that websocket connection. |
| Websocket request with `session_id` | Uses the named session, allowing one connection to drive multiple games. |

When a websocket connection closes, Minorail closes the sessions used by that
connection.

---

## Authoritative Snapshot

Minorail treats every incoming snapshot as authoritative.

| Field | Meaning |
| --- | --- |
| `board` | Physical board cells. |
| `active` | Current active piece. |
| `queue` | Upcoming pieces, excluding active. |
| `hold` | Hold piece or null. |
| `can_hold` | Whether hold is currently legal. |
| `seq` | Sequence number for the observed state. |
| `last_move` | Optional previous placement. |

Minorail does not require the caller to be perfectly synchronized. Mismatches
are normal and are handled through reconciliation.

---

## Status Values

| Status | Meaning | Bot action |
| --- | --- | --- |
| `synced` | First request, or incoming physical state matches the session. | Start or keep. |
| `advanced` | Incoming state matches the expected result of the previous selected placement. | Send `advance` and any `new_piece` messages. |
| `reconciled` | Incoming state did not exactly match, but Minorail preserved bot session continuity. | Send `board`, or send `advance` plus `board`. |
| `reset` | Incoming state required a bot session restart from the authoritative snapshot. | Send `stop` plus `start`, or restart a closed bot process from snapshot. |
| `invalid` | Request validation failed. | Do not contact the bot. |
| `no_suggestion` | Bot returned no usable placement before timeout. | Keep session state, but return no placement. |

!> `reconciled` and `reset` are not bot errors. They mean Minorail accepted the
incoming authoritative snapshot and brought the bot session back in line before
asking for the next move.

---

## Reconciliation Reasons

Minorail logs reconciliation details to stderr:

```text
[info] reconciliation: reason=board_changed_after_expected_advance seq=1 action=advance_then_board piece_stream=append
```

| Reason | What changed | Piece stream behavior |
| --- | --- | --- |
| `board_changed_same_piece_stream` | The board changed, but active and queue chronology still match. | Keep alignment. |
| `board_changed_after_expected_advance` | Piece chronology is explainable as an expected advance, but the board does not match exactly. | Append newly observed pieces. |
| `piece_stream_changed_unexpectedly` | Active and queue are not explainable from the previous snapshot. | Realign from observed pieces and mark offset unknown. |
| `rules_changed` | The effective rules changed for an existing session. | Preserve the physical transition's stream behavior. |

If rules change at the same time as a physical mismatch, the logged reason is
`rules_changed`. The `piece_stream` value still describes how Minorail handled
the observed piece chronology.

Board edits through a visualizer commonly produce board-only reconciliation.
Battle garbage rise commonly produces
`board_changed_after_expected_advance`: Minorail first confirms the lock with
`advance` and any `new_piece` messages, then sends `board` for the authoritative
post-garbage physical board when the bot supports it. Bots without `board`
support still use the reset fallback.

---

## Piece Stream Tracking

Minorail tracks generated pieces as:

```text
[active] + queue
```

When the retained stream exceeds `protocol.start.piece_stream_limit`, Minorail
trims older pieces and adjusts the offset when it can.

Set `piece_stream_limit = 0` to omit piece stream data entirely.

Piece stream realignment means Minorail preserves the current observed
`[active] + queue` order but stops asserting an absolute generated-piece offset.
SBP `piece_stream.offset` becomes `null` until later continuity can be inferred
from fresh observations.

---

## Idle Bot Processes

Minorail closes a bot process after the session is idle for `bot.idle_ms`
milliseconds.

The session state remains. On the next request, Minorail starts a new bot
process from the latest known snapshot and continues the session.
