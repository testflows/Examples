from testflows.core import *
from testflows.asserts import error

import actions.game as actions


@TestScenario
def scenario(self):
    """Check Mario can move left in the game."""
    game = self.context.game

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with And("Mario's start position"):
        mario_start = actions.get_element(game, "player")

    with When("press the left key for 1 second"):
        with actions.press_left(game):
            actions.play(game, seconds=1)

    with And("get Mario's end position"):
        mario_end = actions.get_element(game, "player")

    with Then("check Mario moves left"):
        debug(
            f"start: {mario_start.box.x}, end: {mario_end.box.x}, moved: {mario_end.box.x - mario_start.box.x}"
        )
        assert mario_end.box.x < mario_start.box.x, error()
