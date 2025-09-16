from testflows.core import *
from testflows.asserts import error

import actions.game


@TestScenario
def scenario(self):
    """Check Mario can jump in the game."""
    game = self.context.game
    start_frame = len(game.behavior)

    try:
        with Given("get Mario's start position"):
            mario_start = actions.game.get_element(game, "player")

        with When("press the jump key for 0.2 seconds"):
            with actions.game.press_jump():
                actions.game.play(game, seconds=0.2)

        with And("get Mario's end position"):
            mario_end = actions.game.get_element(game, "player")

        with Then("check Mario moves up"):
            debug(
                f"start: {mario_start.box.y}, end: {mario_end.box.y}, moved: {mario_end.box.y - mario_start.box.y}"
            )
            assert mario_end.box.y < mario_start.box.y, error()

    finally:
        with Finally("highlight Mario's start and end positions"):
            actions.game.overlay(game, [mario_start, mario_end])

        with And("save the video"):
            actions.game.save_video(game, path="move_jump.gif", start=start_frame)

        with And("pause until key is pressed to continue"):
            pause()
