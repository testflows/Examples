"""Level behavior model."""

from testflows.core import debug

from .base import Model


class Level(Model):
    """Level behavior model."""

    def __init__(self, game):
        super().__init__(game)
        self.level_num = 1

        # Level boundaries from level_1.json
        self.start_x = 0
        self.end_x = 9086

    def is_at_left_boundary(self, element):
        """Check if element is at the left boundary."""
        return element.box.x == self.start_x

    def is_at_right_boundary(self, element):
        """Check if element is at the right boundary."""
        return element.box.x == self.end_x - element.box.w

    def is_past_left_boundary(self, element):
        """Check if element is past the left boundary (indicates a bug)."""
        return element.box.x < self.start_x

    def is_past_right_boundary(self, element):
        """Check if element is past the right boundary (indicates a bug)."""
        return element.box.x > self.end_x - element.box.w
