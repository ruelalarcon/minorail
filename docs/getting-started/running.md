# Running Minorail

## Requirements

| Requirement | Notes |
| --- | --- |
| Python | 3.11 or newer |
| NiceGUI | Needed for `solo play --web` |
| websockets | Needed for `solo ws` |

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Common Commands

| Task | Command |
| --- | --- |
| Run one solo game with the terminal visualizer | `python minorail.py solo play "path/to/sbp-bot"` |
| Run multiple solo games | `python minorail.py solo play "path/to/sbp-bot" --games 20` |
| Run the solo web visualizer | `python minorail.py solo play "path/to/sbp-bot" --web` |
| Run solo without rendering | `python minorail.py solo play "path/to/sbp-bot" --headless` |
| Run solo evaluation | `python minorail.py solo eval "path/to/sbp-bot" --games 100 --json-out results.json` |
| Start the websocket API | `python minorail.py solo ws "path/to/sbp-bot"` |
| Run a terminal battle | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b"` |
| Run multiple visible battle games | `python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --games 20` |
| Run battle evaluation | `python minorail.py battle eval "path/to/bot-a" "path/to/bot-b" --games 100 --json-out battle.json` |

The top-level CLI is organized by mode:

```text
python minorail.py solo play BOT
python minorail.py solo eval BOT --games N --json-out results.json
python minorail.py solo ws BOT
python minorail.py battle play BOT_A BOT_B --games N
python minorail.py battle eval BOT_A BOT_B --games N --json-out results.json
```

See [Solo](../modes/solo.md), [Battle](../modes/battle.md), and
[Evaluation](../modes/evaluation.md) for mode-specific behavior.

---

## Run Stats

Minorail prints per-game stats to stderr:

```text
[info] pieces=123 elapsed=12.3s pps=10.00
```

Battle play prints the terminal status, winner when there is one, and total
locks. With `--games`, it reuses the same two bot processes across games and
sends stop/start game semantics at each game boundary. Headless battle progress
includes the current incoming garbage count for each player.

For multiple solo games and all evaluation batches, Minorail keeps bot
processes alive when possible. Each finished game sends SBP `stop`, the next
game sends a fresh `start`, and Minorail sends `quit` when the full run ends.
Battle evaluation keeps two bot processes alive across the batch.

If `--piece-limit` or `--time-limit-ms` is provided, the game stops with status
`piece_limit` or `time_limit` when that limit is reached. In battle, the piece
limit counts total accepted locks across both players.

## Pathfinding

Minorail only pathfinds when the selected consumer needs paths. Terminal and
web solo visualizers request paths by default for animation. Battle terminal
also requests paths by default. Headless, null, and evaluation runs do not.

Use `--pathfind` or `--no-pathfind` to override `service.path.pathfinding` and
the consumer default for one invocation.

## Bot Arguments

Solo commands use `--bot-args`:

```bash
python minorail.py solo play "path/to/sbp-bot" --bot-args="--profile fast"
```

Battle commands use per-bot process arguments:

```bash
python minorail.py battle play "bot-a" "bot-b" --bot-a-args="--profile a" --bot-b-args="--profile b"
```

Keep the equals sign when the value starts with a dash. Minorail splits the
string with shell-style parsing before starting the bot.

## WebSocket Mode

Default listener:

```text
ws://127.0.0.1:8444
```

Custom listener:

```bash
python minorail.py solo ws "path/to/sbp-bot" --ws-host 0.0.0.0 --ws-port 9000
```

The default listener comes from `[api.websocket]`. `--ws-host` overrides
`api.websocket.host`; `--ws-port` overrides `api.websocket.port`.

## Related Pages

* [Settings](../reference/settings.md)
* [WebSocket API](../reference/websocket-api.md)
* [Visualizers](../internals/visualizers.md)
