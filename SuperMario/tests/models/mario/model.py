"""
Main Mario behavior model - class-based architecture.

This is the main Mario behavior model class.
"""

from testflows.core import debug
from ..base import Model
from .movement import Movement


class Mario(Model):
    """Mario's behavior model using modular architecture."""

    def __init__(self, game):
        super().__init__(game)
        self.movement = Movement(game=game)

    def expect(self, behavior):
        """Expect Mario to behave correctly."""
        self.movement.expect(behavior)
