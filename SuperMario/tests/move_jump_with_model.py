from testflows.core import *

import actions.game as actions


@TestScenario
def scenario(self):
    """Check Mario can jump in the game."""
    game = self.context.game
    model = self.context.model

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with When("press the jump key for 1 frame then play for 0.5 seconds"):
        with actions.press_jump():
            actions.play(game, frames=1, model=model)
        actions.play(game, seconds=0.5, model=model)
