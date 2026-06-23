# Minorail

> A local Tetris game runner for bots that implement the [Stacker Bot Protocol (SBP)](https://github.com/ruelalarcon/stacker_bot_protocol).

Minorail provides an SBP bot a complete local game to play against. Minorail owns the
board, active piece, queue, hold state, rules, and sequence numbers, while the
bot focuses on choosing placements. It can reconcile queue and board state
across requests, repair desyncs when observed state changes unexpectedly,
generate movement paths for selected placements.

Minorail also exposes the same suggestion flow over websockets, allowing you to
easily connect real game clients to your SBP bot by sending game state updates
to Minorail's websocket API.

# Screenshots

<img width="auto" height="500" alt="web_visualizer" src="https://github.com/user-attachments/assets/394f76be-7d1b-4f49-b2b0-182a9ebe22b4" />

<img width="auto" height="500" alt="terminal_visualizer" src="https://github.com/user-attachments/assets/e288fa1d-a836-4c7a-a8c5-2b076a14a2be" />

## Features

| Feature | What it does |
| --- | --- |
| Solo local Tetris game | Runs one board, active piece, queue, hold, line clears, combo, and back to back state. |
| Battle mode | Runs two SBP bots against each other with configurable attack calculators and garbage rules. |
| SBP bot runner | Starts an SBP bot subprocess and exchanges `rules`, `start`, `suggest`, `play`, `new_piece`, `stop`, and `quit` messages. |
| Terminal visualizer | Shows a local game directly in the terminal. |
| Web visualizer | Provides a browser based view for watching games and inspecting state. |
| Headless runs | Runs batches without rendering for testing or benchmarking. |
| Evaluation output | Writes JSON summaries and lock-by-lock events for batch analysis. |
| Websocket API | Serves Minorail suggestions to external clients while keeping per session state. |
| Session reconciliation | Treats incoming snapshots as authoritative and resets or advances the bot session as needed. |
| Piece stream tracking | Keeps generated piece chronology aligned for bots that support SBP `piece_stream`. |
| Path output | Finds input paths to selected placements and can convert sonic drops to soft drops. |
| Rule settings | Supports randomizer, kickset, 180s, sonic drop mode, all spin back to back, perfect-clear back to back, and spawn position settings. |

## Documentation

Detailed documentation is available here:

https://ruelalarcon.github.io/minorail/

SBP protocol documentation is available here:

https://github.com/ruelalarcon/stacker_bot_protocol

## Installation

Minorail requires Python 3.11 or newer.

```bash
pip install -r requirements.txt
```

## Quick Start

Run one game with the terminal visualizer:

```bash
python minorail.py solo play "path/to/sbp-bot"
```

Run with the web visualizer:

```bash
python minorail.py solo play "path/to/sbp-bot" --web
```

Run a headless batch:

```bash
python minorail.py solo play "path/to/sbp-bot" --headless --games 100
```

Run a JSON evaluation batch:

```bash
python minorail.py solo eval "path/to/sbp-bot" --games 100 --seed 123 --json-out results.json
```

Limit a run by accepted piece locks or wall-clock time:

```bash
python minorail.py solo eval "path/to/sbp-bot" --games 100 --piece-limit 1000 --time-limit-ms 30000
```

Run a two-bot battle:

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b"
```

Run a battle in the web visualizer:

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --web
```

Run multiple battle games while reusing the two bot processes:

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --games 20
```

Run battle evaluation:

```bash
python minorail.py battle eval "path/to/bot-a" "path/to/bot-b" --games 100 --json-out battle-results.json
```

Start the websocket API:

```bash
python minorail.py solo ws "path/to/sbp-bot"
```

## Settings

Minorail reads `settings.toml` by default. Use `--settings` to load another
file:

```bash
python minorail.py solo play "path/to/sbp-bot" --settings custom-settings.toml
```

Settings cover gameplay rules, bot timeouts, queue refill behavior, pathfinding,
bot info logging, and visualizer timing.

## Development

Run tests:

```bash
python -m pytest
```

Run lint and type checks:

```bash
./lint.sh
```

On Windows PowerShell:

```powershell
.\lint.ps1
```
