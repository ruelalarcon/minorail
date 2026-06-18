# Visualizers

Minorail has several ways to observe a local game.

## Terminal

```bash
python run.py "path/to/sbp-bot" --terminal
```

The terminal visualizer is the default. It renders game state in the terminal
and animates returned paths.

## Web

```bash
python run.py "path/to/sbp-bot" --web
```

The web visualizer uses NiceGUI and opens a browser based view.

Options:

```bash
python run.py "path/to/sbp-bot" --web --web-host 127.0.0.1 --web-port 8080
```

The default bind address comes from `[visualizer.web]`. `--web-host` overrides
`visualizer.web.host`; `--web-port` overrides `visualizer.web.port`. If no web
port is set there or on the CLI, Minorail chooses one automatically.

## Headless

```bash
python run.py "path/to/sbp-bot" --headless
```

Headless mode runs without rendering and prints progress logs.

This is useful for batch runs.

## Visualizer Timing

Timing settings are in `[visualizer]`:

```toml
[visualizer]
move_delay_ms = 50
lock_delay_ms = 150
first_move_delay_ms = 200
visible_rows = 20
queue_size = 5

[visualizer.web]
host = "127.0.0.1"
# port = 8080
```

These settings affect rendering only.

## Board Edits

Visualizers can request board edits through engine controls.

Supported controls:

* set one cell filled or empty
* clear the board
* read the current state

When a board edit changes state, Minorail increments the sequence number and
clears `last_move`. The next suggestion request may resync the bot if the edit
changed physical state.
