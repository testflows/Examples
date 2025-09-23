from testflows.core import *

import actions.game as actions


@TestScenario
@Name("move right")
def scenario(self):
    """Check Mario can move right in the game."""
    game = self.context.game
    model = self.context.model

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with When("press the right key for 1 second"):
        with actions.press_right():
            actions.play(game, seconds=1, model=model)
