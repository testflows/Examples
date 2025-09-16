from testflows.core import *
from testflows.asserts import error

import actions.game


@TestScenario
@Name("move left")
def scenario(self):
    """Check Mario can move left in the game."""
    game = self.context.game
    model = self.context.model
    start = len(game.behavior)
    end = -1

    try:
        with When("press the left key for 1 second"):
            with actions.game.press_left():
                actions.game.play(game, seconds=1, model=model)
    finally:
        with Finally("highlight Mario's start and end positions"):
            actions.game.overlay(
                game,
                [
                    actions.game.get_element(game, "player", frame=start),
                    actions.game.get_element(game, "player", frame=end),
                ],
            )

        with And("save the video"):
            actions.game.save_video(game, path="move_left.gif", start=start)

        with And("pause until key is pressed to continue"):
            pause()
