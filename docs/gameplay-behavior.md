# Gameplay Behavior

This page describes Minorail behavior that affects gameplay results and
suggestion output.

---

## Board And Coordinates

Minorail uses a 10 by 40 board.

| Item | Behavior |
| --- | --- |
| x axis | Increases from left to right. |
| y axis | Increases upward. |
| Row 0 | Bottom row. |
| Default spawn | `x = 4`, `y = 19`, `rotation = North`. |
| Internal board | `cols[x]` has bit `y` set when cell `(x, y)` is occupied. |

SBP board matrices and websocket board matrices use the same coordinate system:
row arrays are ordered from bottom to top, `null` means empty, and any string
means occupied.

---

## Piece Definitions

The built-in Minorail piece set is the seven tetromino strings:

```text
I O T L J S Z
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

Piece identifiers are not inherently limited to tetrominoes. A fork or
extension can add pieces with arbitrary non-empty string identifiers, including
larger or smaller mino pieces, as long as the game client, Minorail instance,
and bot all use the SBP piece definition standard: identifiers, anchor
coordinates, relative cells, rotation names, spawn behavior, kicks, and lock
rules must agree. Programs with a different internal piece model are
responsible for translating to this standard at the API or SBP boundary.

Websocket callers are responsible for sending snapshots and placements that
match the piece definitions supported by the Minorail instance they are using.

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
| Spin clear with `allspin_b2b` | Incremented. | Incremented. |
| All clear with `allclear_b2b` | Incremented. | Incremented. |

---

## Spin Behavior

Placements carry a spin value:

| Spin | Meaning |
| --- | --- |
| `none` | Not a spin. |
| `mini` | Mini spin. |
| `full` | Full spin. |

Minorail uses T-spin and T-spin mini clears for back to back handling by
default. When `allspin_b2b = true`, spin clears from other pieces also
contribute.

?> For pieces other than T, Minorail detects spins using immobility.

---

## Top Out

After each piece locks, Minorail ends the local game if any board cell exists
at or above row 20.
