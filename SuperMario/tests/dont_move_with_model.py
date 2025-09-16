from testflows.core import *

import actions.game


@TestScenario
@Name("don't move")
def scenario(self):
    """Check Mario's behavior when not keys are pressed."""
    game = self.context.game
    model = self.context.model
    start = len(game.behavior)
    end = -1

    try:
        with When("play the game without touching any keys for 1 second"):
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
            actions.game.save_video(game, path="dont_move.gif", start=start)

        with And("pause until key is pressed to continue"):
            pause()
