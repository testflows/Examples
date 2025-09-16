import os
import sys

from testflows.core import *

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Hides the pygame welcome message
append_path(sys.path, os.path.join(current_dir(), ".."), pos=0)

import actions.game
import models.game


@TestFeature
def regression(self):
    """Run tests for the Super Mario Bros. game."""

    with Given("start the game"):
        self.context.game = actions.game.start()

    with And("create game model"):
        self.context.model = models.game.Game(self.context.game)

    with And("play the game for 3 frames"):
        actions.game.play(self.context.game, frames=3, model=self.context.model)

    Scenario(run=load("tests.move_jump_with_model", "scenario"))
    # Scenario(run=load("tests.move_right_with_model", "scenario"))
    # Scenario(run=load("tests.move_left_with_model", "scenario"))
    # Scenario(run=load("tests.dont_move_with_model", "scenario"))


if main():
    regression()
