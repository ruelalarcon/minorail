from __future__ import annotations

import sys
import time
from typing import Any, Optional

from core.board import Board
from core.piece import Piece
from core.placement import Placement
from core.rotation import Rotation
from display.renderer import render
from game.randomizer import Randomizer, make_randomizer
from game.rules import Rules
from game.state import GameState
from movegen.pathfinder import MoveStep, apply_step
from service.move_selection import moving_piece_for
from service.snapshot import ObservedSnapshot, SuggestionRequest
from service.suggestion_service import SuggestionService


class Frontend:
    def __init__(
        self, bot_path: str, settings: dict[str, dict[str, Any]], display: bool = True
    ):
        self._bot_path = bot_path
        self._settings = settings
        self._display = display

    def _render(
        self,
        state: GameState,
        piece: Optional[Piece] = None,
        loc: Optional[tuple[int, int, Rotation]] = None,
    ) -> None:
        cfg = self._settings["display"]
        render(state, piece, loc, cfg["visible_rows"], cfg["queue_size"])

    def _ensure_queue_refilled(
        self,
        state: GameState,
        rand: Randomizer,
        refill_at: int,
    ) -> None:
        while len(state.queue) < refill_at:
            state.queue.append(rand.next())

    def _snapshot(
        self,
        state: GameState,
        seq: int,
        last_move: Optional[Placement],
    ) -> ObservedSnapshot:
        return ObservedSnapshot(
            board=state.board.copy(),
            current=state.current_piece(),
            queue=list(state.queue),
            hold=state.hold,
            can_hold=not state.hold_used_this_turn,
            seq=seq,
            last_move=last_move,
        )

    def play_game(self) -> dict[str, Any]:
        protocol_cfg = self._settings.get("protocol", {})
        service = SuggestionService(
            self._bot_path,
            piece_stream_limit=protocol_cfg.get("piece_stream_limit", 11),
        )

        cfg_d = self._settings["display"]
        cfg_b = self._settings["bot"]
        move_delay = cfg_d["move_delay_ms"] / 1000
        lock_delay = cfg_d["lock_delay_ms"] / 1000
        refill_at = self._settings["queue"]["refill_threshold"]

        rules = Rules.from_settings(self._settings)

        rand = make_randomizer(rules.randomizer)
        assert rand is not None
        state = GameState(
            board=Board(),
            queue=[rand.next() for _ in range(self._settings["queue"]["initial"])],
            hold=None,
            combo=0,
            back_to_back=0,
        )

        if self._display:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

        pieces_placed = 0
        start_time = time.time()
        first_move = True
        seq = 0
        last_move: Optional[Placement] = None

        try:
            while True:
                self._ensure_queue_refilled(state, rand, refill_at)

                spawn_piece = state.current_piece()
                if spawn_piece is None:
                    break

                if self._display:
                    self._render(state, spawn_piece, (4, 19, Rotation.North))

                if first_move:
                    time.sleep(cfg_b["first_move_think_ms"] / 1000)
                result = service.suggest(
                    SuggestionRequest(
                        snapshot=self._snapshot(state, seq, last_move),
                        rules=rules,
                        include_path=True,
                        session_id="terminal",
                        timeout_ms=cfg_b["suggest_timeout_ms"],
                    )
                )
                first_move = False
                seq += 1
                if result.placement is None:
                    print(
                        f"[frontend] no suggestion: {result.reason or result.status.value}",
                        file=sys.stderr,
                    )
                    break

                chosen = result.placement

                placed_piece = chosen.location.piece
                hold_used = placed_piece != spawn_piece

                moving_piece = moving_piece_for(
                    self._snapshot(state, seq, last_move), chosen
                )
                if moving_piece is None:
                    print(f"[frontend] no valid move: {chosen}", file=sys.stderr)
                    break

                if self._display:
                    path = result.path

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
                                step,
                                moving_piece,
                                arot,
                                ax,
                                ay,
                                state.board,
                                rules.kickset,
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
                        print(
                            f"[frontend] warning: {result.reason or 'no path found'}",
                            file=sys.stderr,
                        )
                        loc = chosen.location
                        self._render(state, moving_piece, (loc.x, loc.y, loc.rotation))

                    time.sleep(lock_delay)

                ok = state.apply_move(chosen, rules)
                if not ok:
                    print(f"[frontend] apply_move rejected: {chosen}", file=sys.stderr)
                    break

                last_move = chosen
                self._ensure_queue_refilled(state, rand, refill_at)

                pieces_placed += 1

                if self._display:
                    self._render(state)
                    time.sleep(lock_delay * 0.5)

                if any(state.board.cols[x] >> 20 != 0 for x in range(10)):
                    if self._display:
                        self._render(state)
                    print("[frontend] topped out", file=sys.stderr)
                    break
        finally:
            elapsed = time.time() - start_time
            service.close()

        return {
            "pieces": pieces_placed,
            "elapsed": elapsed,
            "pps": pieces_placed / elapsed if elapsed > 0 else 0,
        }
