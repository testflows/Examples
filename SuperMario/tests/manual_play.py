from testflows.core import *

import actions.game as actions


@TestScenario
def scenario(self, play_seconds=30):
    """Allow manual play of the game for a specified duration with behavior model validation."""
    game = self.context.game
    model = self.context.model

    with Given("setup for manual play"):
        actions.setup(game=game, overlays=[])

    with When(f"playing manually for {play_seconds} seconds"):
        # Enable manual mode so all keys are captured
        game.manual = True

        with By(
            "starting manual play session",
            description=f"""Controls:
            - Arrow Keys: Move Mario left/right/down
            - A: Jump
            - S: Action (run/fire)
            - Enter: Pause/Menu
            - Close window or wait {play_seconds} seconds to finish
            
            Note: Mario's behavior will be validated by the behavior model
            during play. Any physics violations will be reported as test failures.""",
        ):

            # Play for the specified duration with model validation
            actions.play(game, seconds=play_seconds, model=model)

    with Then("manual play session completed"):
        game.manual = False
        note("Manual play session finished!")
