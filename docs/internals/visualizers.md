# Visualizers

Minorail separates solo visualizers from battle visualizers. Solo visualizers
observe one board through the `SoloVisualizer` protocol. Battle visualizers
observe two boards through `BattleVisualizer`.

## Solo

Terminal:

```bash
python minorail.py solo play "path/to/sbp-bot" --terminal
```

The terminal visualizer is the solo default. It renders game state in the
terminal and animates returned paths.

Web:

```bash
python minorail.py solo play "path/to/sbp-bot" --web
python minorail.py solo play "path/to/sbp-bot" --web --web-host 127.0.0.1 --web-port 8080
```

The web visualizer uses NiceGUI and opens a browser-based view. The default bind
address comes from `[visualizer.web]`.

Headless:

```bash
python minorail.py solo play "path/to/sbp-bot" --headless
```

Headless mode runs without rendering and prints progress logs.

## Battle

Terminal:

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --terminal
```

The battle terminal visualizer shows both boards side by side, animates
suggestion paths when pathfinding is enabled, and displays each player's
incoming garbage count.

Headless:

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --headless
```

Headless battle mode prints periodic lock progress and incoming garbage counts.

Null:

```bash
python minorail.py battle play "path/to/bot-a" "path/to/bot-b" --null
```

Null battle mode produces no visual output. Battle evaluation uses this mode.

There is no battle web visualizer yet. The battle visualizer protocol is
separate so a future `visualizers.battle.web` can render two-player state
without forcing battle behavior into the solo API.

## Visualizer Timing

Solo and battle visualizers use the same `[visualizer]` timing settings:

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

Visualizers that support edits request them through runner controls rather than
mutating `GameState.board` directly. Solo currently exposes cell edits and clear
board controls. Battle visualizers are observers for now.
