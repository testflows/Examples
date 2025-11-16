"""
Main Mario behavior model - class-based architecture.

This is the main Mario behavior model class.
"""

from testflows.core import note
from ..base import Model
from .movement import Movement


class Mario(Model):
    """Mario's behavior model using modular architecture."""

    def __init__(self, game):
        super().__init__(game)
        self.movement = Movement(game=game)

    def expect(self, behavior, debug=True):
        """Expect Mario to behave correctly."""
        try:
            self.movement.expect(behavior)
        except AssertionError as e:
            if debug:
                note(f"Model assertion failed: {e}")
                backtrack = 5
                note(f"Last {backtrack} states (most recent last):")
                for index, state in enumerate(behavior[-backtrack:]):
                    note(f"-{backtrack-index} state: {state}")
            raise
