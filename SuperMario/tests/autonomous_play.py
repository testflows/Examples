import random

from testflows.core import *

import models.game as models
import actions.game as actions
import actions.moves as moves
import actions.paths as paths


def select_weighted_move(weights=None):
    """Select a move with weighted probabilities."""
    move_weights = []
    move_functions = []

    if weights is None:
        weights = {
            "fuzzy": 10.0,
            "right": 2.0,
            "left": 0.5,
        }

    for move in moves.all_moves:
        weight = weights.get(move.__name__, 1.0)
        move_weights.append(weight)
        move_functions.append(move)

    return random.choices(move_functions, weights=move_weights, k=1)[0]


@TestScenario
def play(self, path, play_seconds=1, with_model=False):
    """Allow autonomous play of the game for a specified duration
    with behavior model validation."""

    with Given("start the game"):
        self.context.game = actions.start(quit=False)

    game = self.context.game

    with Given("setup for autonomous play"):
        actions.setup(game=game, overlays=[])

    if with_model:
        self.context.model = models.Game(game)

    model = self.context.model

    length = play_seconds * game.fps
    new_path = []
    game_path = paths.GamePath()

    while len(new_path) < length:
        move = select_weighted_move()
        if move.__name__ == "fuzzy":
            new_path += move(length=length - len(new_path))
        else:
            new_path += move()

    # Use triangular distribution biased towards complete sequence
    sequence_length = len(path.input_sequence)
    stop_fraction = random.triangular(0, 1.05, 1.05)  # mode slightly above 1
    stop_index = max(1, min(sequence_length, round(stop_fraction * sequence_length)))

    # If playing the best path, stop at the end of the path
    if self.context.always_pick_full_path:
        stop_index = sequence_length + 1

    note(f"Playing {stop_index - 1} of {sequence_length} frames from path")

    # Skip index 0 (the old dummy frame) since game_path already has a new dummy
    for i, input in enumerate(path.input_sequence[1:stop_index], start=1):
        actions.press_keys(game, input)
        actions.play(game, frames=1, model=model)
        game_path.append(input, game.behavior[-1])
        if game_path.scores[-1] != path.scores[i]:
            note(
                f"Replay score mismatch on frame {i}: {game_path.scores[-1]} != {path.scores[i]}"
            )
            raise RuntimeError("Replay score mismatch")
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
    interval=20,
    tries=3,
    save_paths=True,
    load_paths=True,
    paths_file="paths.json",
    with_model=False,
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
    self.context.paths = paths.GamePaths(paths=[paths.GamePath()])

    if load_paths:
        with Given("load paths from file"):
            paths.load(filename=paths_file)

    path = self.context.paths.select()

    for part in range(play_seconds // interval):
        for i in range(tries):
            with Scenario(f"interval {part}-{i}"):
                play(
                    path=path,
                    play_seconds=interval,
                    with_model=with_model,
                )

            if path not in self.context.paths.paths:
                # If the path is no longer in the paths list
                # so we stop playing it
                break

        # Select the next path
        self.context.paths.clean()
        path = self.context.paths.select()

        # Save all paths to file if requested
        if save_paths:
            with Then("save paths to file"):
                paths.save(filename=paths_file)
