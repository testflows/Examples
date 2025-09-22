from .base import Model
from .mario import Mario


class Game(Model):
    """Game model."""

    def __init__(self, game):
        super().__init__(game)
        self.mario = Mario(game=game)

    def expect(self, behavior):
        """Expect the game to behave correctly."""
        self.mario.expect(behavior)
