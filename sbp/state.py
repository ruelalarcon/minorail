from __future__ import annotations

from sbp.messages import MsgStart
from tetris.game.state import GameState, spawn_location
from tetris.model.rules import Rules


def game_state_from_start(message: MsgStart, rules: Rules | None = None) -> GameState:
    rules = rules or Rules()
    return GameState(
        board=message.board.copy(),
        active=spawn_location(
            message.active,
            x=rules.spawn_x,
            y=rules.spawn_y,
        ),
        queue=list(message.queue),
        hold=message.hold,
        combo=message.combo,
        back_to_back=message.back_to_back,
    )
