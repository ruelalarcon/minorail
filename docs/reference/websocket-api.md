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

## Request Shape

Each request is a JSON text frame.

```json
{
  "type": "suggest",
  "seq": 7,
  "board": { "cols": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] },
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
| `board` | object or matrix | Column bitboard object or SBP row matrix. |
| `active` | string | Piece string. |
| `queue` | string array | Upcoming pieces only. |

Optional fields:

| Field | Default | Notes |
| --- | --- | --- |
| `type` | `suggest` | Only `suggest` is accepted. |
| `hold` | null | Piece string or null. |
| `can_hold` | true | Whether hold is currently legal. |
| `last_move` | null | SBP placement or null. |
| `rules` | server settings | Partial per request rule override. |
| `extensions` | null | Object forwarded to the bot. |
| `pathfinding` | server settings; true when omitted | Whether Minorail should pathfind the selected placement. |
| `convert_sonic_drops` | server settings | Whether returned paths rewrite intermediate sonic drops. Only matters when pathfinding is enabled. |
| `session_id` | connection session | Non empty string. |
| `timeout_ms` | settings value | Positive integer. |

---

## Board Formats

The preferred Minorail board format is column bitboards:

```json
{
  "board": {
    "cols": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  }
}
```

`cols[x]` has bit `y` set when cell `(x, y)` is occupied. Each column must fit
in 40 bits.

The API also accepts an SBP board matrix:

```json
{
  "board": [
    [null, null, null, null, null, null, null, null, null, null]
  ]
}
```

The full matrix must contain 40 rows with 10 cells each. Row 0 is the bottom.
`null` is empty. Any string is occupied.

Board coordinates use the same grid convention in every request and response:

| Item | Meaning |
| --- | --- |
| `x = 0` | Leftmost column. |
| `y = 0` | Bottom row. |
| `x` direction | Increases to the right. |
| `y` direction | Increases upward. |
| Matrix rows | Ordered from bottom to top. |
| Matrix cells | `null` is empty; any string is occupied. |

---

## Pieces

Piece fields use SBP piece strings:

```text
I O T L J S Z
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
    "spawn_x": 4,
    "spawn_y": 20
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
| `spawn_x` | integer |
| `spawn_y` | integer |

Unknown rule fields are rejected.

When spawn coordinates are overridden, Minorail spawns the active piece at
those coordinates for that request.

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

```json
{
  "type": "suggest",
  "session_id": "game-42",
  "seq": 12,
  "board": { "cols": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] },
  "active": "I",
  "queue": ["T", "L", "J"]
}
```

When the websocket connection closes, Minorail closes every session used by
that connection.

---

## Extensions

`extensions` must be an object. Minorail forwards it to the SBP bot in `start`
and `suggest` messages.

Example:

```json
{
  "extensions": {
    "minorail.garbage.v1": {
      "incoming_garbage": 4
    }
  }
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
| `status` | `synced`, `advanced`, `resynced`, `invalid`, or `no_suggestion`. |
| `placements` | All parsed placements returned by the bot. |
| `placement` | Selected usable placement or null. |
| `path` | Input path or null. |
| `reason` | Diagnostic text or null. |

When a placement is selected, it uses SBP placement shape.

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
* missing or invalid `seq`
* unknown request types
* invalid board shape
* board columns outside 40 bits
* invalid piece strings
* unknown rule fields
* non object extensions
* empty session ids
* non positive timeouts
