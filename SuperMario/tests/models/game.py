from .base import Model
from .mario import Mario
from .level import Level


class Game(Model):
    """Game model."""

    def __init__(self, game):
        super().__init__(game)
        self.level = Level(game=game)
        self.mario = Mario(game=game, level=self.level)

    def expect(self, behavior):
        """Expect the game to behave correctly."""
        self.mario.expect(behavior)
