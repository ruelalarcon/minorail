# Minorail

> A local Tetris engine and bot runner for bots that implement the [Stacker Bot Protocol (SBP)](https://github.com/ruelalarcon/stacker_bot_protocol).

Minorail provides an SBP bot a complete local game to play against. Minorail owns the
board, active piece, queue, hold state, rules, and sequence numbers, while the
bot focuses on choosing placements. It can reconcile queue and board state
across requests, repair desyncs when observed state changes unexpectedly,
generate movement paths for selected placements.

Minorail also exposes the same suggestion flow over websockets, allowing you to
easily connect real game clients to your SBP bot by sending game state updates
to Minorail's websocket API.

## Features

| Feature | What it does |
| --- | --- |
| Local Tetris engine | Runs the board, active piece, queue, hold, line clears, combo, and back to back state. |
| SBP bot runner | Starts an SBP bot subprocess and exchanges `rules`, `start`, `suggest`, `play`, `new_piece`, `stop`, and `quit` messages. |
| Terminal visualizer | Shows a local game directly in the terminal. |
| Web visualizer | Provides a browser based view for watching games and inspecting state. |
| Headless runs | Runs batches without rendering for testing or benchmarking. |
| Websocket API | Serves Minorail suggestions to external clients while keeping per session state. |
| Resync handling | Treats incoming snapshots as authoritative and resets or advances the bot session as needed. |
| Piece stream tracking | Keeps generated piece chronology aligned for bots that support SBP `piece_stream`. |
| Path output | Finds input paths to selected placements and can convert sonic drops to soft drops. |
| Configurable rules | Supports randomizer, kickset, 180s, sonic drop mode, all spin back to back, all clear back to back, and spawn position settings. |

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
python run.py "path/to/sbp-bot"
```

Run with the web visualizer:

```bash
python run.py "path/to/sbp-bot" --web
```

Run a headless batch:

```bash
python run.py "path/to/sbp-bot" --headless --games 100
```

Start the websocket API:

```bash
python run.py "path/to/sbp-bot" --ws
```

## Configuration

Minorail reads `settings.toml` by default. Use `--settings` to load another
file:

```bash
python run.py "path/to/sbp-bot" --settings custom-settings.toml
```

Settings cover gameplay rules, bot timeouts, queue refill behavior, path output
options, bot info logging, and visualizer timing.

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
