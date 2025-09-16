from testflows.core import *
from testflows.asserts import error

import actions.game


@TestScenario
def scenario(self):
    """Check Mario can move right in the game."""
    game = self.context.game

    try:
        with Given("get Mario's start position"):
            mario_start = actions.game.get_element(game, "player")

        with When("press the right key for 1 second"):
            with actions.game.press_right():
                actions.game.play(game, seconds=1)

        with And("get Mario's end position"):
            mario_end = actions.game.get_element(game, "player")

        with Then("check Mario moves right"):
            debug(
                f"start: {mario_start.box.x}, end: {mario_end.box.x}, moved: {mario_end.box.x - mario_start.box.x}"
            )
            assert mario_end.box.x > mario_start.box.x, error()

    finally:
        with Finally("highlight Mario's start and end positions"):
            actions.game.overlay(game, [mario_start, mario_end])

        with And("save the video"):
            actions.game.save_video(game, path="move_right.gif")

        with And("pause until key is pressed to continue"):
            pause()
