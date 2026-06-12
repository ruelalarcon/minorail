# Sessions And Resyncs

Minorail sessions preserve bot continuity across suggestion requests.

?> Use sessions when you want the bot to keep its internal state between
suggestions. Use separate `session_id` values for independent games.

This matters because an SBP bot session has internal state. If Minorail can
prove that the new snapshot is the expected result of the last selected
placement, it advances the bot with `play` and `new_piece`. If not, it resets
the bot from the authoritative snapshot.

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

Minorail does not require the caller to be perfectly synchronized. Desync is a
normal case.

---

## Status Values

| Status | Meaning | Bot action |
| --- | --- | --- |
| `synced` | First request, or incoming physical state matches the session. | Start or keep. |
| `advanced` | Incoming state matches the expected result of the previous selected placement. | Send `play` and any `new_piece` messages. |
| `resynced` | Incoming state does not match the previous physical state or expected advance. | Reset from the incoming snapshot. |
| `invalid` | Request validation failed. | Do not contact the bot. |
| `no_suggestion` | Bot returned no usable placement before timeout. | Keep session state, but return no placement. |

!> `resynced` is not an error. It means Minorail repaired the bot session
before asking for the next move.

---

## Resync Types

Minorail logs resync details to stderr:

```text
[info] minorail resync: type=board_changed_after_expected_advance seq=1 bot_action=reset piece_stream_action=append
```

| Type | What changed | Piece stream behavior |
| --- | --- | --- |
| `board_changed_same_piece_stream` | The board changed, but active and queue chronology still match. | Keep alignment. |
| `board_changed_after_expected_advance` | Piece chronology is explainable as an expected advance, but the board does not match exactly. | Append newly observed pieces. |
| `piece_stream_changed_unexpectedly` | Active and queue are not explainable from the previous snapshot. | Resync from observed pieces and mark offset unknown. |
| `rules_changed` | The effective rules changed for an existing session. | Preserve the physical transition's stream behavior. |

If rules change at the same time as a physical desync, the logged type is
`rules_changed`. The `piece_stream_action` still describes how Minorail handled
the observed piece chronology.

Board edits through a visualizer commonly produce a board-only resync.

---

## Piece Stream Tracking

Minorail tracks generated pieces as:

```text
[active] + queue
```

When the retained stream exceeds `protocol.start.piece_stream_limit`, Minorail
trims older pieces and adjusts the offset when it can.

Set `piece_stream_limit = 0` to omit piece stream data entirely.

---

## Idle Bot Processes

If `bot.idle_ms` is positive, Minorail closes a bot process after the session is
idle for that long.

The session state remains. On the next request, Minorail starts a new bot
process from the latest known snapshot and continues the session.
