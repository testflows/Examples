from testflows.core import *

import actions.game as actions


@TestScenario
@Name("don't move")
def scenario(self):
    """Check Mario's behavior when not keys are pressed."""
    game = self.context.game
    model = self.context.model

    with Given("setup and cleanup"):
        actions.setup(game=game, overlays=[("player", 0), ("player", -1)])

    with When("play the game without touching any keys for 1 second"):
        actions.play(game, seconds=1, model=model)
