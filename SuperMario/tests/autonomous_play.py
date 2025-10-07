import random
from testflows.core import *
import actions.game as actions


def generate_input(starting_keys, flip_probability, length):
    input = []
    next_keys = starting_keys

    for _ in range(length):
        for key_name, pressed in next_keys.items():
            if random.random() < flip_probability:
                next_keys[key_name] = not pressed
        input.append(next_keys)
        next_keys = next_keys.copy()
    return input


@TestScenario
def play(self, input_sequence, play_seconds=1):
    """Allow autonomous play of the game for a specified duration
    with behavior model validation."""

    with Given("start the game"):
        game = actions.start(quit=False)
        self.context.game = game

    starting_keys = {
        "right": False,
        "left": False,
        "down": False,
        "jump": False,
        "action": False,
        "enter": False,
    }

    input_sequence += generate_input(
        starting_keys, flip_probability=0.10, length=play_seconds * game.fps
    )

    for input in input_sequence:
        actions.press_keys(game, input)
        actions.play(game, frames=1)

    self.context.paths.append((input_sequence, game.behavior))


def score_paths(path):
    """Score the path based on the player's position."""
    _, behavior = path
    now = behavior[-1]

    if now.player is None:
        return 0

    return now.player.x_pos


@TestScenario
def scenario(self, play_seconds, interval=1, tries=5):
    """Allow autonomous play of the game for a specified duration
    with behavior model validation."""

    self.context.paths = []

    input_sequence = []

    for part in range(play_seconds // interval):
        for i in range(tries):
            with Scenario(f"{part}:try {i}"):
                play(input_sequence=input_sequence, play_seconds=interval)

        # Sort paths by score (best first)
        paths = self.context.paths
        paths.sort(key=score_paths, reverse=True)
        scores = [score_paths(path) for path in paths]

        # Display all scores
        note(f"All scores: {scores}")
        note(f"Best score: {scores[0]}")

        # Pick path using probability distribution - higher scores more likely
        min_score = min(scores)
        weights = [s - min_score + 1 for s in scores]  # +1 to avoid zero weights
        selected_idx = random.choices(range(len(paths)), weights=weights, k=1)[0]

        input_sequence = paths[selected_idx][0]
        note(f"Selected path score: {scores[selected_idx]}")
