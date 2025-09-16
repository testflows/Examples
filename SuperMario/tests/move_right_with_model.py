from testflows.core import *

import actions.game


@TestScenario
@Name("move right")
def scenario(self):
    """Check Mario can move right in the game."""
    game = self.context.game
    model = self.context.model
    start = len(game.behavior)
    end = -1

    try:
        with When("press the right key for 1 second"):
            with actions.game.press_right():
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
            actions.game.save_video(game, path="move_right.gif", start=start)

        with And("pause until key is pressed to continue"):
            pause()
