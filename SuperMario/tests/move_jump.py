from testflows.core import *
from testflows.asserts import error

import actions.game as actions


@TestScenario
def scenario(self):
    """Check Mario can jump in the game."""
    game = self.context.game

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with And("Mario's start position"):
        mario_start = actions.get_element(game, "player")

    with When("press the jump key for 0.2 seconds"):
        with actions.press_jump():
            actions.play(game, seconds=0.2)

    with And("get Mario's end position"):
        mario_end = actions.get_element(game, "player")

    with Then("check Mario moves up"):
        debug(
            f"start: {mario_start.box.y}, end: {mario_end.box.y}, moved: {mario_end.box.y - mario_start.box.y}"
        )
        assert mario_end.box.y < mario_start.box.y, error()
