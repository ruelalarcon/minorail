# Gameplay Behavior

This page describes Minorail behavior that affects gameplay results and
suggestion output.

---

## Board And Coordinates

Minorail defaults to a 10 by 40 board. `protocol.rules.board_size.width` and
`protocol.rules.board_size.height` can configure another size for local runs
and websocket requests.

| Item | Behavior |
| --- | --- |
| x axis | Increases from left to right. |
| y axis | Increases upward. |
| Row 0 | Bottom row. |
| Default spawn | `x = 4`, `y = 20`, `rotation = North`. |
| Internal board | `rows[y][x]` is a byte cell id. `0` is empty; nonzero is occupied. |

Minorail stores board cells as byte rows. Cell id `0` is empty, `1..7` map to
the built-in pieces in `IJLOSTZ` order, and `8` is garbage. Other nonzero cell
ids are treated as occupied and use the same generic visual color as garbage.
Minorail itself does not impose a 64-row board-height limit. SBP bots may
advertise narrower board-size support; Frostetra, for example, supports width
10 and heights from 1 through 64.

SBP board matrices and websocket board matrices use the same coordinate system:
row arrays are ordered from bottom to top, `null` means empty, and any non-null
cell means occupied. Known cell labels preserve visual color; unknown non-null
cells become generic garbage-colored cells. Matrix dimensions must match the
active board-size rules.

---

## Piece Definitions

The built-in Minorail piece set is the seven tetromino strings:

```text
I J L O S T Z
```

Each piece definition is identified by a string and consists of relative
occupied cell offsets for each rotation. Minorail's built-in rotation names are
`north`, `east`, `south`, and `west`; placements use an anchor coordinate
`(x, y)`, and each relative cell `[dx, dy]` occupies absolute board cell
`(x + dx, y + dy)`.

Example built-in north-facing cells:

| Piece | `north` relative cells |
| --- | --- |
| `I` | `[[-1, 0], [0, 0], [1, 0], [2, 0]]` |
| `O` | `[[0, 0], [1, 0], [0, 1], [1, 1]]` |
| `T` | `[[-1, 0], [0, 0], [1, 0], [0, 1]]` |
| `L` | `[[-1, 0], [0, 0], [1, 0], [1, 1]]` |
| `J` | `[[-1, 0], [0, 0], [1, 0], [-1, 1]]` |
| `S` | `[[-1, 0], [0, 0], [0, 1], [1, 1]]` |
| `Z` | `[[-1, 1], [0, 1], [0, 0], [1, 0]]` |

Stock Minorail currently supports only these seven built-in tetrominoes. The
SBP piece definition standard is broader than that, but supporting additional
piece identifiers would require extending Minorail's piece model, geometry,
kicks, randomizers, and parsing together.

Websocket callers are responsible for sending snapshots and placements that use
the built-in Minorail piece definitions.

---

## Queue Semantics

The queue excludes the active piece everywhere in Minorail public behavior.

| Location | Queue meaning |
| --- | --- |
| Local `GameState.queue` | Upcoming pieces only. |
| Websocket request `queue` | Upcoming pieces only. |
| SBP `start.queue` | Upcoming pieces only. |
| Piece stream tracking | `[active] + queue`. |

---

## Hold Semantics

Minorail infers hold use from the selected placement.

| Placement piece | Legal when |
| --- | --- |
| Active piece | Always, if the placement fits. |
| Current hold piece | `can_hold` is true. |
| First upcoming piece | `can_hold` is true and hold is empty. |

If the selected placement cannot be explained by those rules, Minorail rejects
it.

---

## Move Selection

Bots can return multiple placements in one suggestion.

Minorail chooses the first placement that:

* fits the current board
* can be made with active or hold semantics

?> Minorail treats the bot's placement ordering as meaningful. A later
placement can be ignored even if it is better.

---

## Pathfinding

When `pathfinding` is true, Minorail tries to find a path from spawn to the
selected placement.

| Input | Used for |
| --- | --- |
| Spawn position | Initial BFS state. |
| Kickset | Rotation attempts. |
| `rot180` | Whether 180 degree rotations are allowed. |
| `sonic_drop` | Whether soft drop movement is allowed. |
| Current board | Collision and drop distance checks. |

A successful path ends with `hard_drop`.

Possible steps:

| Step | Meaning |
| --- | --- |
| `left`, `right` | One cell horizontal movement. |
| `das_left`, `das_right` | Move horizontally until blocked. |
| `rot_cw`, `rot_ccw`, `rot_180` | Rotation attempts using the configured kickset. |
| `soft_drop` | Move down one row. |
| `sonic_drop` | Drop to the grounded y position without locking. |
| `hard_drop` | Lock the piece. |

If no path is found, Minorail can still return the selected placement. The
response path is null and `reason` explains that no path was found.

---

## Sonic Drop Conversion

If `service.path.convert_sonic_drops` or request `convert_sonic_drops` is true,
Minorail rewrites intermediate `sonic_drop` steps into repeated `soft_drop`
steps.

The final `hard_drop` lock step is left unchanged.

?> This conversion affects Minorail output only. It does not change SBP rules.

---

## Line Clears

Minorail applies the selected placement to the local board, clears full rows,
then updates combo and back to back state.

| Clear result | Combo | Back to back |
| --- | --- | --- |
| No rows clear | Reset to 0. | Preserved. |
| Normal line clear | Incremented. | Reset to 0. |
| Four line clear | Incremented. | Incremented. |
| T-spin or T-spin mini clear | Incremented. | Incremented. |
| Clear with a source in `back_to_back_sources` | Incremented. | Incremented. |

---

## Spin Behavior

Placements carry a spin value:

| Spin | Meaning |
| --- | --- |
| `none` | Not a spin. |
| `mini` | Mini spin. |
| `full` | Full spin. |

Minorail uses `spin_detection` to classify lock spins and `back_to_back_sources` to
decide which clear classes maintain back to back. By default, quads, T-spins,
and T-spin minis maintain back to back. Non-T spins and perfect-clears can be added
with `allspin`, `allspin-mini`, and `perfect-clear` source atoms.

`allspin` and `allspin-mini` exclude T pieces. T-piece spins use `t-spin` and
`t-spin-mini`.

Spin detection modes:

| Mode | Behavior |
| --- | --- |
| `none` | No spins are detected. |
| `t-spins` | T pieces use T-spin corner and kick detection. Non-T pieces are not spins. |
| `t-spins+` | `t-spins`, plus immobile T-piece fallback as mini. |
| `all` | T pieces use T-spin detection. Immobile non-T pieces are full spins. |
| `all+` | `all`, plus immobile T-piece fallback as mini. |
| `all-mini` | T pieces use T-spin detection. Immobile non-T pieces are mini spins. |
| `all-mini+` | `all-mini`, plus immobile T-piece fallback as mini. |
| `mini-only` | T pieces force detected T-spins to mini. Immobile T and non-T pieces are mini spins. |

---

## Top Out

After each piece locks, Minorail ends the local game if any board cell exists
at or above row 20.
