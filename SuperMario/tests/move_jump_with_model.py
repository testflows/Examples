from testflows.core import *

import actions.game as actions


@TestScenario
def scenario(self):
    """Check Mario can jump in the game."""
    game = self.context.game
    model = self.context.model

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with When("press right and jump keys for 0.2 seconds"):
        with actions.press_right():
            with actions.press_jump():
                actions.play(game, seconds=0.2, model=model)
