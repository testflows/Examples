from testflows.core import *

import actions.game as actions


@TestScenario
@Name("move left")
def scenario(self):
    """Check Mario can move left in the game."""
    game = self.context.game
    model = self.context.model

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with When("press the left key for 1 second"):
        with actions.press_left():
            actions.play(game, seconds=1, model=model)
