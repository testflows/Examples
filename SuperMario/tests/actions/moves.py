import random

import actions.game as actions

from testflows.core import *

all_moves = []


def move(func):
    """Decorator to add a move to the all_moves list."""
    all_moves.append(func)
    return func


@move
def fuzzy(
    starting_keys: actions.PressedKeys = None,
    flip_probability: float = 0.10,
    length: int = 30,
):
    """Generate a sequence of input actions."""
    inputs = []
    current_keys = starting_keys

    if current_keys is None:
        current_keys = actions.get_pressed_keys(current().context.game)

    for _ in range(length):
        current_keys = actions.PressedKeys(
            **{
                k: (
                    (0 if getattr(current_keys, k) else 1)
                    if random.random() < flip_probability
                    else getattr(current_keys, k)
                )
                for k in current_keys.__struct_fields__
            }
        )

        inputs.append(current_keys)

    return inputs


@move
def stay_still_long(length: int = 30):
    return [actions.PressedKeys(right=0, left=0, jump=0, action=0, enter=0)] * length


@move
def stay_still_short(length: int = 5):
    return [actions.PressedKeys(right=0, left=0, jump=0, action=0, enter=0)] * length


@move
def walk_right_long(length: int = 30):
    return [actions.PressedKeys(right=1)] * length


@move
def walk_left_long(length: int = 30):
    return [actions.PressedKeys(left=1)] * length


@move
def run_right_long(length: int = 30):
    return [actions.PressedKeys(right=1, action=1)] * length


@move
def run_left_long(length: int = 30):
    return [actions.PressedKeys(left=1, action=1)] * length


@move
def jump_up_high(length: int = 60):
    return [actions.PressedKeys(jump=1)] * length


@move
def jump_up_right_high(length: int = 60):
    return [actions.PressedKeys(jump=1, right=1)] * length


@move
def jump_up_left_high(length: int = 60):
    return [actions.PressedKeys(jump=1, left=1)] * length


@move
def jump_up_right_high_action(length: int = 60):
    return [actions.PressedKeys(jump=1, right=1, action=1)] * length


@move
def jump_up_left_high_action(length: int = 60):
    return [actions.PressedKeys(jump=1, left=1, action=1)] * length


@move
def down(length: int = 5):
    return [actions.PressedKeys(down=1)] * length
