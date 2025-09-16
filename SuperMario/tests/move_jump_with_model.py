from testflows.core import *

import actions.game


@TestScenario
def scenario(self):
    """Check Mario can jump in the game."""
    game = self.context.game
    model = self.context.model
    start = len(game.behavior) - 1
    end = -1

    try:
        with When("press the jump key for 1 frame then play for 1 second"):
            with actions.game.press_jump():
                actions.game.play(game, frames=1, model=model)
            actions.game.play(game, seconds=0.5, model=model)

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
            actions.game.save_video(game, path="move_jump.gif", start=start)

        with And("pause until key is pressed to continue"):
            pause()
