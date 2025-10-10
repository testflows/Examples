import random

from testflows.core import *

import actions.game as actions
import actions.moves as moves
import actions.paths as paths


def select_weighted_move():
    """Select a move with weighted probabilities:
    - fuzzy gets 40% weight (for exploration)
    - right moves get 2x weight over left moves
    - other moves get normal weight
    """
    move_weights = []
    move_functions = []

    for move in moves.all_moves:
        weight = 1.0
        move_name = move.__name__

        # Give fuzzy much higher weight for exploration
        if move_name == "fuzzy":
            weight = 5.0
        # Prefer right moves over left moves
        elif "right" in move_name:
            weight = 5.0
        elif "left" in move_name:
            weight = 0.5

        move_weights.append(weight)
        move_functions.append(move)

    return random.choices(move_functions, weights=move_weights, k=1)[0]


@TestScenario
def play(self, path, play_seconds=1, model=None):
    """Allow autonomous play of the game for a specified duration
    with behavior model validation."""

    with Given("start the game"):
        game = actions.start(quit=False, fps=60 * 5)

    length = play_seconds * game.fps
    new_path = []
    game_path = paths.GamePath()

    while len(new_path) < length:
        move = select_weighted_move()
        if move.__name__ == "fuzzy":
            new_path += move(length=length - len(new_path))
        else:
            new_path += move()

    for input in path.input_sequence:
        actions.press_keys(game, input)
        actions.play(game, frames=1, model=model)
        game_path.append(input, game.behavior[-1])
        if game_path.deaths[-1]:
            self.context.paths.delete(path)
            return

    for input in new_path[:length]:
        actions.press_keys(game, input)
        actions.play(game, frames=1, model=model)
        game_path.append(input, game.behavior[-1])
        if game_path.deaths[-1]:
            break

    self.context.paths.add(game_path)


@TestScenario
def scenario(
    self,
    play_seconds,
    interval=30,
    tries=3,
    save_paths=True,
    load_paths=True,
    paths_file="paths.json",
):
    """Allow autonomous play of the game for a specified duration
    with behavior model validation.

    Args:
        play_seconds: Total duration to play
        interval: Interval for each iteration
        tries: Number of tries per interval
        save_paths: If True, save all discovered paths to file
        load_paths: If True, load existing paths from file as starting pool
        paths_file: Path to JSON file for storing/loading paths
    """
    self.context.model = None  # Turn off model for now
    self.context.paths = paths.GamePaths(paths=[paths.GamePath()])

    if load_paths:
        with Given("load paths from file"):
            paths.load(filename=paths_file)

    path = self.context.paths.select()

    for part in range(play_seconds // interval):
        for i in range(tries):
            with Scenario(f"interval {part}:try {i}"):
                play(path=path, play_seconds=interval, model=self.context.model)

            if path not in self.context.paths.paths:
                # If the path is no longer in the paths list
                # so we stop playing it
                break

        # Select the next path
        path = self.context.paths.select()

        # Save all paths to file if requested
        if save_paths:
            with Then("save paths to file"):
                paths.save(filename=paths_file)
