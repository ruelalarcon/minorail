# Running Minorail

## Requirements

| Requirement | Notes |
| --- | --- |
| Python | 3.11 or newer |
| NiceGUI | Needed for `--web` |
| websockets | Needed for `--ws` |

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Common Commands

| Task | Command |
| --- | --- |
| Run one game with the terminal visualizer | `python run.py "path/to/sbp-bot"` |
| Run multiple games | `python run.py "path/to/sbp-bot" --games 20` |
| Run the web visualizer | `python run.py "path/to/sbp-bot" --web` |
| Run without rendering | `python run.py "path/to/sbp-bot" --headless` |
| Run with a piece cap | `python run.py "path/to/sbp-bot" --piece-limit 1000` |
| Run with a time cap | `python run.py "path/to/sbp-bot" --time-limit-ms 30000` |
| Start the websocket API | `python run.py "path/to/sbp-bot" --ws` |

?> The terminal visualizer is the default unless `--web`, `--headless`, or
`--ws` is selected.

---

## Game Stats

Minorail prints per game stats to stderr:

```text
[info] pieces=123 elapsed=12.3s pps=10.00
```

For multiple games, it also prints total pieces.

If `--piece-limit` or `--time-limit-ms` is provided, the game stops with status
`piece_limit` or `time_limit` when that limit is reached.

## Bot Arguments

Pass extra bot arguments with `--bot-args`:

```bash
python run.py "path/to/sbp-bot" --bot-args="--profile fast --nodes 5000"
```

Keep the equals sign when the value starts with a dash:

```bash
python run.py "path/to/sbp-bot" --bot-args="--profile fast"
```

Minorail splits this string with shell style parsing before starting the bot.

---

## Settings File

Minorail loads `settings.toml` by default:

```bash
python run.py "path/to/sbp-bot"
```

Use another settings file:

```bash
python run.py "path/to/sbp-bot" --settings custom-settings.toml
```

Missing settings fall back to built in defaults.

---

## WebSocket Mode

Default listener:

```text
ws://127.0.0.1:8444
```

Custom listener:

```bash
python run.py "path/to/sbp-bot" --ws --ws-host 0.0.0.0 --ws-port 9000
```

!> Websocket mode cannot be combined with terminal, web, or headless visualizer
modes in the same process.
