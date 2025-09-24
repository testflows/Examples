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

    def should_stay_at_boundary(self, element, direction):
        """Check if element should stay at boundary and not move further."""

        if direction == "right":
            # Check if element was already at the right boundary
            if self.is_at_right_boundary(element):
                debug(
                    f"{element.name.capitalize()} at right boundary at x={element.box.x}, level end_x={self.end_x}"
                )
                return True
            elif self.is_past_right_boundary(element):
                # This should never happen - element past the boundary indicates a bug
                assert (
                    False
                ), f"{element.name.capitalize()} is past right boundary! x={element.box.x}, boundary={self.end_x - element.box.w}"
        elif direction == "left":
            # Check if element was already at the left boundary
            if self.is_at_left_boundary(element):
                debug(
                    f"{element.name.capitalize()} at left boundary at x={element.box.x}, level start_x={self.start_x}"
                )
                return True
            elif self.is_past_left_boundary(element):
                # This should never happen - element past the boundary indicates a bug
                assert (
                    False
                ), f"{element.name.capitalize()} is past left boundary! x={element.box.x}, start_x={self.start_x}"

        return False
