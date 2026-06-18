# Settings

Minorail reads settings from TOML. The default file is `settings.toml`.

Settings are merged over built in defaults from `config/settings.py`, so a
custom file can contain only the fields you want to change.

?> Settings affect two things: Minorail's local engine behavior and the SBP
rules or start data sent to the bot. Visualizer settings only affect display.

---

## Protocol Rules

```toml
[protocol.rules]
randomizer = "seven_bag"
kickset = "srs"
rot180 = true
sonic_drop = "only"
allspin_b2b = true
allclear_b2b = true
spawn_x = 4
spawn_y = 19
```

These rules are used locally and are sent to the SBP bot in the `rules`
message.

| Field | Values | Behavior |
| --- | --- | --- |
| `randomizer` | `seven_bag`, `pure_random` | Controls how Minorail generates pieces for local games. |
| `kickset` | `srs`, `srs_plus` | Controls local rotation and pathfinding behavior. |
| `rot180` | `true`, `false` | Enables 180 degree rotations when the kickset has the transition data. |
| `sonic_drop` | `only`, `allow` | Controls whether pathfinding can use soft drops, sonic drops, or both. |
| `allspin_b2b` | `true`, `false` | Lets non `none` spin clears continue back to back. |
| `allclear_b2b` | `true`, `false` | Lets all clears continue back to back. |
| `spawn_x` | integer | Active piece spawn x coordinate. |
| `spawn_y` | integer | Active piece spawn y coordinate. |

!> Startup fails if the bot reports capabilities that do not support configured
rules such as the randomizer, kickset, `rot180`, sonic drop mode, or custom
spawn position.

?> Minorail handles spins for pieces other than T through immobility based spin
detection.

Default spawn:

```text
x = 4
y = 19
rotation = North
```

`sonic_drop` is sent as an SBP rule. It is separate from
`service.path.convert_sonic_drops`, which only changes returned paths.

---

## Start Options

```toml
[protocol.start]
piece_stream_limit = 11
```

| Field | Behavior |
| --- | --- |
| `piece_stream_limit` | Maximum number of generated pieces included in `start.piece_stream`. |

Use `0` to omit piece stream data.

If a bot does not support `piece_stream`, Minorail logs a warning and omits the
field.

---

## Service Path Options

```toml
[service.path]
# pathfinding = false
convert_sonic_drops = false
```

| Field | Behavior |
| --- | --- |
| `pathfinding` | Optional boolean. Omit it to use the selected consumer's pathfinding preference. `true` always runs pathfinding by default. `false` skips pathfinding by default. CLI `--pathfind` and `--no-pathfind` override `service.path.pathfinding` for one invocation. |
| `convert_sonic_drops` | Converts intermediate `sonic_drop` path steps into repeated `soft_drop` steps when pathfinding is enabled. |

The final `hard_drop` remains unchanged.

These are service pathfinding options. They do not change the SBP rules sent
to the bot.

Terminal and web visualizers prefer paths by default because they can animate
them. Headless runs and evaluation do not request paths by default.

---

## Bot Options

```toml
[bot]
suggest_timeout_ms = 10000
idle_ms = 60000
```

| Field | Behavior |
| --- | --- |
| `suggest_timeout_ms` | How long Minorail waits for a usable suggestion before treating the result as no usable suggestion. |
| `idle_ms` | How long a suggestion session can sit idle before Minorail closes the bot process. |

When a bot process goes idle, the session is not forgotten. On the next
request, Minorail starts a new bot process from the latest known state.

`idle_ms` must be a positive integer.

---

## API Options

```toml
[api.websocket]
host = "127.0.0.1"
port = 8444
```

| Field | Behavior |
| --- | --- |
| `host` | Default bind host for `run.py --ws`. CLI `--ws-host` overrides `api.websocket.host` for one invocation. |
| `port` | Default bind port for `run.py --ws`. CLI `--ws-port` overrides `api.websocket.port` for one invocation. |

---

## Bot Info Logging

```toml
[logging.bot_info]
print = ["warning", "log"]
```

| Field | Behavior |
| --- | --- |
| `print` | Runtime SBP `info` topics Minorail prints. |

For example, if `print = ["warning"]`, `info` messages with topic `status` are
ignored.

---

## Engine Queue

```toml
[engine.randomizer]
seed = 0

[engine.limits]
piece_limit = 1000
time_limit_ms = 30000

[engine.queue]
initial = 5
refill_threshold = 5
```

| Field | Behavior |
| --- | --- |
| `engine.randomizer.seed` | Optional integer default base seed for reproducible local piece streams. Omit it to use entropy unless a CLI seed override is provided. |
| `engine.limits.piece_limit` | Optional integer default accepted piece lock limit. Omit it to run until another terminal condition occurs. |
| `engine.limits.time_limit_ms` | Optional integer default wall-clock game time limit in milliseconds. Omit it to run until another terminal condition occurs. |
| `initial` | Number of generated pieces available at game start, including the active piece. |
| `refill_threshold` | Minorail refills the upcoming queue until its length reaches this value. |

For example, `initial = 5` creates one active piece and four upcoming pieces.

`GameState.queue` and websocket request `queue` values contain upcoming pieces
only. They never include the active piece.

When running multiple games through `run.py --games`, Minorail derives each
game seed as `seed + game_index`, where `game_index` starts at `0`. For example,
`--seed 100 --games 3` uses seeds `100`, `101`, and `102`.

`run.py --seed` overrides `engine.randomizer.seed` for one invocation. If both
are provided, the CLI value wins.

`run.py --piece-limit` overrides `engine.limits.piece_limit`;
`run.py --time-limit-ms` overrides `engine.limits.time_limit_ms`. If the
matching setting is also set, the CLI value wins.

---

## Visualizer Settings

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

| Field | Behavior |
| --- | --- |
| `move_delay_ms` | Delay between animated input steps. |
| `lock_delay_ms` | Pause after a piece locks. |
| `first_move_delay_ms` | Pause before animating the first move. |
| `visible_rows` | Number of board rows shown by visualizers. |
| `queue_size` | Number of upcoming pieces shown by visualizers. |
| `visualizer.web.host` | Default bind host for `run.py --web`. CLI `--web-host` overrides `visualizer.web.host` for one invocation. |
| `visualizer.web.port` | Default bind port for `run.py --web`. Omit it to choose an open port automatically. CLI `--web-port` overrides `visualizer.web.port` for one invocation. |

These settings affect presentation only. They do not change local rules, SBP
messages, or websocket responses.
