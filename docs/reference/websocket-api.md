# WebSocket API

Minorail can expose the suggestion service over a websocket API.

?> The websocket API is Minorail's API, not SBP. It accepts snapshots from a
client, then Minorail talks to the SBP bot internally.

Start it with:

```bash
python minorail.py solo ws "path/to/sbp-bot"
```

Default endpoint:

```text
ws://127.0.0.1:8444
```

Custom endpoint:

```bash
python minorail.py solo ws "path/to/sbp-bot" --ws-host 0.0.0.0 --ws-port 9000
```

The default endpoint comes from `[api.websocket]` in settings. `--ws-host`
overrides `api.websocket.host`; `--ws-port` overrides `api.websocket.port`.

---

## Suggest Request Shape

Each request is a JSON text frame.

```js
{
  "type": "suggest",
  "seq": 7,
  "board": [
    [null, null, null, null, null, null, null, null, null, null],
    ...,
    [null, null, null, null, null, null, null, null, null, null]
  ],
  "active": "T",
  "queue": ["I", "O", "L", "J"],
  "hold": null,
  "can_hold": true,
  "pathfinding": true
}
```

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `seq` | integer | Non negative sequence number. |
| `board` | matrix | SBP row matrix. |
| `active` | string | Piece string. |
| `queue` | string array | Upcoming pieces only. |

Optional fields:

| Field | Default | Notes |
| --- | --- | --- |
| `type` | `suggest` | Suggestion request type. |
| `hold` | null | Piece string or null. |
| `can_hold` | true | Whether hold is currently legal. |
| `last_move` | null | SBP placement or null. |
| `rules` | server settings | Partial per request rule override. |
| `incoming_garbage` | null | Null, omitted, or pending garbage chunks as positive integers. |
| `extensions` | null | Object forwarded to the bot. |
| `pathfinding` | server settings; true when omitted | Whether Minorail should pathfind the selected placement. |
| `convert_sonic_drops` | server settings | Whether returned paths rewrite intermediate sonic drops. Only matters when pathfinding is enabled. |
| `session_id` | connection session | Non empty string. |
| `timeout_ms` | settings value | Positive integer. |

---

## Advance Request Shape

Clients that intend to execute a returned suggestion may send an `advance` message
as soon as they accept the selected placement:

```json
{
  "type": "advance",
  "seq": 7,
  "session_id": "game-42",
  "placement": {
    "location": {
      "type": "T",
      "orientation": "north",
      "x": 4,
      "y": 1
    },
    "spin": "none"
  }
}
```

Minorail translates this into SBP `advance` for the bot. The next normal
`suggest` snapshot remains authoritative: Minorail uses it to append newly
observed queue pieces and reconcile the bot. If the actual post-lock state
differs only by board cells, Minorail sends a board update to bots that support
it. If active piece, queue, hold state, or rules differ, Minorail resets the
bot session from the authoritative snapshot.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `type` | string | Must be `advance`. |
| `placement` | object | SBP placement selected from a prior suggestion. |

Optional fields:

| Field | Default | Notes |
| --- | --- | --- |
| `seq` | null | Echoed in the response when present. |
| `session_id` | connection session | Must match the session that produced the suggestion. |
| `rules` | server settings | Partial per request rule override; use the same effective rules as the matching `suggest`. |

---

## Close Session Request Shape

Clients can explicitly close a Minorail session without closing the websocket:

```json
{
  "type": "close_session",
  "seq": 13,
  "session_id": "game-42"
}
```

Minorail closes the session state and any live SBP bot process for that
`session_id`. A later `suggest` with the same `session_id` starts a fresh
session from that request's snapshot.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `type` | string | Must be `close_session`. |

Optional fields:

| Field | Default | Notes |
| --- | --- | --- |
| `seq` | null | Echoed in the response when present. |
| `session_id` | connection session | Non empty string. |

---

## Board Formats

The preferred Minorail board format is an SBP-style row matrix:

```js
{
  "board": [
    [null, null, null, null, null, null, null, null, null, null],
    ...,
    [null, null, null, null, null, null, null, null, null, null]
  ]
}
```

The full matrix must contain `board_size.height` rows with `board_size.width`
cells each. Row 0 is the bottom. `null` is empty. Any non-null value is
occupied. Known string labels `"I"`, `"J"`, `"L"`, `"O"`, `"S"`, `"T"`,
`"Z"`, and `"G"` are preserved internally for visualizer colors; other
non-null values are treated as generic garbage-colored occupied cells.

Board coordinates use the same grid convention in every request and response:

| Item | Meaning |
| --- | --- |
| `x = 0` | Leftmost column. |
| `y = 0` | Bottom row. |
| `x` direction | Increases to the right. |
| `y` direction | Increases upward. |
| Matrix rows | Ordered from bottom to top. |
| Matrix cells | `null` is empty; any non-null value is occupied. |

---

## Pieces

Piece fields use SBP piece strings:

```text
I J L O S T Z
```

Those seven tetromino identifiers are the built-in Minorail pieces. Stock
Minorail currently rejects other piece strings. The SBP piece definition
standard is broader than that, but supporting additional identifiers would
require extending Minorail's piece model, geometry, kicks, randomizers, and
parsing together.

The websocket API takes `active` as a piece string, not as a full location
object. Minorail spawns it at the configured spawn position.

The `queue` contains upcoming pieces only. It must not include the active
piece.

!> Passing the active piece inside `queue` will desync the chronology Minorail
uses for session advancement.

!> Websocket clients are responsible for sending built-in Minorail piece
strings and placements in SBP's piece geometry convention. If a client uses a
different internal coordinate system or rotation origin, it must translate to
SBP's system before sending requests.

---

## Rules Override

A request can include partial rule overrides:

```json
{
  "rules": {
    "kickset": "srs_plus",
    "rot180": true,
    "spawn_position": { "x": 4, "y": 20 },
    "board_size": { "width": 10, "height": 40 }
  }
}
```

| Field | Type |
| --- | --- |
| `randomizer` | string |
| `kickset` | string |
| `rot180` | boolean |
| `sonic_drop` | string |
| `spin_detection` | string |
| `back_to_back_sources` | array of strings |
| `spawn_position` | object with integer `x` and `y` |
| `board_size` | object with positive integer `width` and `height` |

Unknown rule fields are rejected.

When spawn coordinates are overridden, Minorail spawns the active piece at
those coordinates for that request.

When board size is overridden, the request board must match that size.
`board_size.height` is not capped by Minorail. SBP bots may still reject sizes
outside their advertised board-size capabilities.

Rules are evaluated on every request. If the effective rules for an existing
session change, Minorail resets the internal bot session from the incoming
snapshot before asking for the next suggestion. Re-sending the same rules on
every request is safe; unchanged rules are not re-sent to the SBP bot.

---

## Sessions

If `session_id` is omitted, Minorail creates one default session for the
websocket connection.

Provide `session_id` when one connection needs to drive multiple independent
games:

```js
{
  "type": "suggest",
  "session_id": "game-42",
  "seq": 12,
  "board": [
    [null, null, null, null, null, null, null, null, null, null],
    ...,
    [null, null, null, null, null, null, null, null, null, null]
  ],
  "active": "I",
  "queue": ["T", "L", "J"]
}
```

When the websocket connection closes, Minorail closes every session used by
that connection. To retire a session while keeping the websocket open, send
`close_session`.

---

## Extensions

`extensions` must be an object. Minorail forwards it to the SBP bot in `start`
and `suggest` messages.

Example:

```json
{
  "extensions": {
    "minorail.example.v1": {
      "value": true
    }
  }
}
```

---

## Incoming Garbage

`incoming_garbage` may be omitted, `null`, or an array of positive integers.
Omitted or `null` means incoming garbage is unknown or not provided. An empty
array means it is known and currently empty. Non-empty arrays are ordered from
earliest-resolving garbage chunk to latest-resolving chunk.

```json
{
  "incoming_garbage": [4, 2]
}
```

---

## Success Response

```json
{
  "type": "suggestion",
  "seq": 7,
  "status": "synced",
  "placements": [],
  "placement": null,
  "path": null,
  "reason": "bot returned no usable placement"
}
```

| Field | Meaning |
| --- | --- |
| `seq` | Copied from the request. |
| `status` | `synced`, `advanced`, `reconciled`, `reset`, `invalid`, or `no_suggestion`. |
| `placements` | All parsed placements returned by the bot. |
| `placement` | Selected usable placement or null. |
| `path` | Input path or null. |
| `reason` | Diagnostic text or null. |

When a placement is selected, it uses SBP placement shape.

`advance` responses use this shape:

```json
{
  "type": "advance",
  "seq": 7,
  "accepted": true
}
```

`accepted` is `false` when Minorail has no matching active suggestion/session
to begin early advance for that placement. The client can continue normally; the
next `suggest` snapshot will use the standard reconciliation path.

`close_session` responses use this shape:

```json
{
  "type": "close_session",
  "seq": 13,
  "closed": true
}
```

`closed` is `false` when no live session existed for that id. Closing an
already-closed session is not an error.

---

## Error Response

```json
{
  "type": "error",
  "seq": 7,
  "reason": "invalid_request",
  "message": "active must be a piece string"
}
```

| Reason | Meaning |
| --- | --- |
| `invalid_request` | The request could not be parsed or validated. |
| `bot_startup_failed` | The SBP bot failed to register, accept rules, or support configured rules. |
| `internal_error` | An unexpected server error occurred. |

---

## Validation Rules

The API rejects:

* non JSON text frames
* JSON values that are not objects
* missing `suggest` sequence numbers or invalid `seq` values
* unknown request types
* invalid board shape
* invalid piece strings
* invalid advance placements
* invalid close session ids
* unknown rule fields
* non object extensions
* empty session ids
* non positive timeouts
