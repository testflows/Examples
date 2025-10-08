import random
import actions.game as actions


def random_move(
    starting_keys: actions.PressedKeys, flip_probability: float, length: int
):
    """Generate a sequence of input actions."""
    inputs = []
    current = starting_keys

    for _ in range(length):
        current = actions.PressedKeys(
            **{
                k: (
                    (0 if getattr(current, k) else 1)
                    if random.random() < flip_probability
                    else getattr(current, k)
                )
                for k in current.__struct_fields__
            }
        )

        inputs.append(current)

    return inputs
