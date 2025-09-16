from testflows.core import *
from testflows.asserts import error

import actions.game


@TestScenario
def scenario(self):
    """Check Mario can move left in the game."""
    game = self.context.game
    start_frame = len(game.behavior)

    try:
        with Given("get Mario's start position"):
            mario_start = actions.game.get_element(game, "player")

        with When("press the left key for 1 second"):
            with actions.game.press_left():
                actions.game.play(game, seconds=1)

        with And("get Mario's end position"):
            mario_end = actions.game.get_element(game, "player")

        with Then("check Mario moves left"):
            debug(
                f"start: {mario_start.box.x}, end: {mario_end.box.x}, moved: {mario_end.box.x - mario_start.box.x}"
            )
            assert mario_end.box.x < mario_start.box.x, error()

    finally:
        with Finally("highlight Mario's start and end positions"):
            actions.game.overlay(game, [mario_start, mario_end])

        with And("save the video"):
            actions.game.save_video(game, path="move_left.gif", start=start_frame)

        with And("pause until key is pressed to continue"):
            pause()
