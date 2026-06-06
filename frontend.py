from __future__ import annotations

import sys
import threading
import time
from typing import Any, Optional

from bot.process import BotProcess
from core.board import Board, piece_cells
from core.piece import Piece
from core.placement import Placement
from core.rotation import Rotation
from display.renderer import render
from game.randomizer import Randomizer, make_randomizer
from game.rules import Rules
from game.state import GameState
from movegen.pathfinder import MoveStep, apply_step, find_path
from tbp.messages import MsgStart


class Frontend:
    def __init__(
        self, bot_path: str, settings: dict[str, dict[str, Any]], display: bool = True
    ):
        self._bot_path = bot_path
        self._settings = settings
        self._display = display
        self._suggestion_event = threading.Event()
        self._suggestion: Optional[list[Placement]] = None
        self._ready_event = threading.Event()

    def _on_bot_message(self, obj: dict[str, Any]) -> None:
        match obj.get("type"):
            case "info":
                print(
                    f"[info] {obj.get('name')} {obj.get('version')} by {obj.get('author')}",
                    file=sys.stderr,
                )
            case "ready":
                self._ready_event.set()
            case "suggestion":
                self._suggestion = [Placement.from_tbp(m) for m in obj.get("moves", [])]
                self._suggestion_event.set()
            case "error":
                print(f"[bot error] {obj.get('reason')}", file=sys.stderr)

    def _build_start(self, rules: Rules) -> tuple[MsgStart, Randomizer]:
        n = self._settings["queue"]["initial"]
        rand = make_randomizer(rules.randomizer, {})
        assert rand is not None
        queue = [rand.next() for _ in range(n)]
        bag_state = rand.peek_bag()
        rand_obj: dict[str, Any] = {"type": rules.randomizer}
        if bag_state:
            rand_obj["bag_state"] = [p.value for p in bag_state]
        msg = MsgStart(
            board=Board(),
            queue=queue,
            hold=None,
            combo=0,
            back_to_back=False,
            randomizer=rand_obj,
        )
        return msg, rand

    def _get_suggestion(self, bot: BotProcess, first: bool) -> list[Placement]:
        cfg = self._settings["bot"]
        if first:
            time.sleep(cfg["first_move_think_ms"] / 1000)
        deadline = time.time() + cfg["suggest_timeout_ms"] / 1000
        while time.time() < deadline:
            self._suggestion_event.clear()
            self._suggestion = None
            bot.send_suggest()
            if not self._suggestion_event.wait(timeout=5.0):
                print("[frontend] timed out waiting for suggestion", file=sys.stderr)
                return []
            moves: list[Placement] = self._suggestion or []
            if moves:
                return moves
            time.sleep(0.05)
        return []

    def _pick_move(
        self, moves: list[Placement], state: GameState
    ) -> Optional[Placement]:
        for candidate in moves:
            loc = candidate.location
            cells = piece_cells(loc.piece, loc.rotation, loc.x, loc.y)
            if not all(
                0 <= x < 10 and 0 <= y < 40 and not state.board.occupied(x, y)
                for (x, y) in cells
            ):
                continue
            placed = loc.piece
            current = state.current_piece()
            if placed == current:
                return candidate
            if state.hold is None:
                if len(state.queue) >= 2 and placed == state.queue[1]:
                    return candidate
            elif placed == state.hold:
                return candidate
        return None

    def _render(
        self,
        state: GameState,
        piece: Optional[Piece] = None,
        loc: Optional[tuple[int, int, Rotation]] = None,
    ) -> None:
        cfg = self._settings["display"]
        render(state, piece, loc, cfg["visible_rows"], cfg["queue_size"])

    def play_game(self) -> dict[str, Any]:
        bot = BotProcess(self._bot_path, self._on_bot_message)
        time.sleep(0.1)

        cfg_d = self._settings["display"]
        move_delay = cfg_d["move_delay_ms"] / 1000
        lock_delay = cfg_d["lock_delay_ms"] / 1000
        refill_at = self._settings["queue"]["refill_threshold"]

        rules = Rules.from_settings(self._settings)

        self._ready_event.clear()
        bot.send_rules(rules)
        if not self._ready_event.wait(timeout=5.0):
            print("[frontend] bot did not send ready", file=sys.stderr)
            bot.send_quit()
            bot.wait()
            return {"pieces": 0}

        start_msg, rand = self._build_start(rules)
        state = GameState.from_start(start_msg, rules.randomizer)
        state.randomizer = rand
        bot.send_start(start_msg)

        if self._display:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

        pieces_placed = 0
        start_time = time.time()
        first_move = True

        while True:
            while len(state.queue) < refill_at:
                p = rand.next()
                state.queue.append(p)
                bot.send_new_piece(p)

            spawn_piece = state.current_piece()
            if spawn_piece is None:
                break

            if self._display:
                self._render(state, spawn_piece, (4, 19, Rotation.North))

            moves = self._get_suggestion(bot, first_move)
            first_move = False
            if not moves:
                print("[frontend] no suggestion", file=sys.stderr)
                break

            chosen = self._pick_move(moves, state)
            if chosen is None:
                print("[frontend] no valid move", file=sys.stderr)
                break

            placed_piece = chosen.location.piece
            hold_used = placed_piece != spawn_piece

            if hold_used:
                if state.hold is None:
                    moving_piece = state.queue[1]
                else:
                    moving_piece = state.hold
            else:
                moving_piece = spawn_piece

            assert moving_piece is not None

            if self._display:
                path = find_path(state.board, moving_piece, chosen.location, rules)

                if hold_used:
                    self._render(state, moving_piece, (4, 19, Rotation.North))
                    time.sleep(lock_delay)

                if path is not None:
                    ax, ay, arot = 4, 19, Rotation.North
                    from movegen.pathfinder import obstructed

                    if obstructed(state.board, moving_piece, arot, ax, ay):
                        ay = 20
                    for step in path[:-1]:
                        ax, ay, arot = apply_step(
                            step, moving_piece, arot, ax, ay, state.board, rules.kickset
                        )
                        self._render(state, moving_piece, (ax, ay, arot))
                        time.sleep(move_delay)
                    ax, ay, arot = apply_step(
                        MoveStep.HardDrop,
                        moving_piece,
                        arot,
                        ax,
                        ay,
                        state.board,
                        rules.kickset,
                    )
                    self._render(state, moving_piece, (ax, ay, arot))
                else:
                    loc = chosen.location
                    self._render(state, moving_piece, (loc.x, loc.y, loc.rotation))

                time.sleep(lock_delay)

            ok = state.apply_move(chosen)
            if not ok:
                print(f"[frontend] apply_move rejected: {chosen}", file=sys.stderr)
                break

            bot.send_play(chosen)
            pieces_placed += 1

            if self._display:
                self._render(state)
                time.sleep(lock_delay * 0.5)

            if any(state.board.cols[x] >> 20 != 0 for x in range(10)):
                if self._display:
                    self._render(state)
                print("[frontend] topped out", file=sys.stderr)
                break

        elapsed = time.time() - start_time
        bot.send_stop()
        bot.send_quit()
        bot.wait(timeout=3.0)
        return {
            "pieces": pieces_placed,
            "elapsed": elapsed,
            "pps": pieces_placed / elapsed if elapsed > 0 else 0,
        }
