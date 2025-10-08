import random

from testflows.core import *

import actions.game as actions
import actions.moves as moves
import actions.paths as paths


@TestScenario
def play(self, path, play_seconds=1, flip_probability=0.10):
    """Allow autonomous play of the game for a specified duration
    with behavior model validation."""

    with Given("start the game"):
        game = actions.start(quit=False)

    if not path:
        starting_keys = actions.PressedKeys(
            right=0,
            left=0,
            down=0,
            jump=0,
            action=0,
            enter=0,
        )
    else:
        starting_keys = path[-1]

    path += moves.random_move(
        starting_keys, flip_probability=flip_probability, length=play_seconds * game.fps
    )

    for input in path:
        actions.press_keys(game, input)
        actions.play(game, frames=1)

    self.context.paths.add(
        paths.GamePath(
            path,
            paths.GamePath.score_path(game.behavior),
            paths.GamePath.hash_path(path),
        )
    )


@TestScenario
def scenario(
    self,
    play_seconds,
    interval=1,
    tries=5,
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

    self.context.paths = paths.GamePaths(paths=[])
    path = []

    if load_paths:
        with Given("load paths from file"):
            paths.load(filename=paths_file)
            path = self.context.paths.select()

    for part in range(play_seconds // interval):
        for i in range(tries):
            with Scenario(f"Part {part}:try {i}"):
                play(
                    path=path,
                    play_seconds=interval,
                    flip_probability=random.choice([0.1]),
                )

        # Sort paths by score (best first)
        self.context.paths.sort()
        path = self.context.paths.select()

        # Save all paths to file if requested
        if save_paths:
            with Then("save paths to file"):
                paths.save(filename=paths_file)
