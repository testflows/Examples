from testflows.core import debug

from ..base import Model


class Propositions:
    """Atomic propositions for Mario's movement."""

    def __init__(self, model):
        self.model = model

    def no_keys(self, right_pressed, left_pressed):
        return not right_pressed and not left_pressed

    def tiny_velocity(self, velocity, threshold=2):
        return abs(velocity) < threshold

    def both_keys_tiny_velocity(
        self, velocity, right_pressed, left_pressed, threshold=3
    ):
        return left_pressed and right_pressed and abs(velocity) < threshold

    def left_touch(self, mario_now, now):
        return self.model.has_left_touch(mario_now, now)

    def left_touched(self, mario_before, before):
        return self.model.has_left_touch(mario_before, before)

    def left_touching(self, mario_now, now, mario_before, before):
        return self.left_touch(mario_now, now) or self.left_touched(
            mario_before, before
        )

    def right_touch(self, mario_now, now):
        return self.model.has_right_touch(mario_now, now)

    def right_touched(self, mario_before, before):
        return self.model.has_right_touch(mario_before, before)

    def right_touching(self, mario_now, now, mario_before, before):
        return self.right_touch(mario_now, now) or self.right_touched(
            mario_before, before
        )

    def at_left_boundary(self, mario_now):
        return self.model.level.is_at_left_boundary(mario_now)

    def at_right_boundary(self, mario_now):
        return self.model.level.is_at_right_boundary(mario_now)

    def has_right_movement_cause(self, velocity, right_pressed):
        return velocity > 0 or right_pressed

    def has_left_movement_cause(self, velocity, left_pressed):
        return velocity < 0 or left_pressed

    def velocity_left(self, velocity):
        return velocity < 0

    def velocity_right(self, velocity):
        return velocity > 0

    def moved_right(self, actual_movement):
        return actual_movement > 0

    def moved_left(self, actual_movement):
        return actual_movement < 0

    def stayed_in_place(self, actual_movement):
        return actual_movement == 0


class CausalProperties(Propositions):
    """Causal properties for Mario's movement."""

    def __init__(self, model):
        self.model = model

    def check_right_movement(self, behavior):
        """Check if Mario's right movement had a valid cause."""
        actual_movement = behavior.actual_movement
        velocity = behavior.velocity
        right_pressed = behavior.right_pressed

        if self.moved_right(actual_movement):
            self.model.assert_with_success(
                self.has_right_movement_cause(velocity, right_pressed),
                f"moved right because {f'velocity is {velocity}' if velocity > 0 else 'right key is pressed'}",
            )

    def check_left_movement(self, behavior):
        """Check if Mario's left movement had a valid cause."""
        actual_movement = behavior.actual_movement
        velocity = behavior.velocity
        left_pressed = behavior.left_pressed

        if self.moved_left(actual_movement):
            self.model.assert_with_success(
                self.has_left_movement_cause(velocity, left_pressed),
                f"moved left because {f'velocity is {velocity}' if velocity < 0 else 'left key is pressed'}",
            )

    def check_stayed_in_place(self, behavior):
        """Check if Mario staying in place had a valid cause."""
        actual_movement = behavior.actual_movement
        velocity = behavior.velocity

        right_pressed = behavior.right_pressed
        left_pressed = behavior.left_pressed

        mario_now = behavior.mario_now
        mario_before = behavior.mario_before

        now = behavior.now
        before = behavior.before

        if self.stayed_in_place(actual_movement):
            self.model.assert_with_success(
                (
                    self.no_keys(right_pressed, left_pressed)
                    or self.tiny_velocity(velocity)
                    or self.both_keys_tiny_velocity(
                        velocity, right_pressed, left_pressed
                    )
                    or (
                        self.velocity_left(velocity)
                        and self.left_touching(mario_now, now, mario_before, before)
                    )
                    or (
                        self.velocity_right(velocity)
                        and self.right_touching(mario_now, now, mario_before, before)
                    )
                    or (
                        self.velocity_left(velocity)
                        and self.at_left_boundary(mario_now)
                    )
                    or (
                        self.velocity_right(velocity)
                        and self.at_right_boundary(mario_now)
                    )
                ),
                "stayed in place",
            )


class Behavior:
    """Encapsulates Mario's movement behavior extracted from behavior frames."""

    @classmethod
    def valid(cls, behavior):
        """Check if behavior frames are valid for movement analysis."""
        return len(behavior) >= 3

    def __init__(self, model, behavior):
        """Extract movement attributes from behavior frames."""
        self.model = model
        self.history = behavior

        if not self.valid(behavior):
            raise ValueError("Need at least 3 frames for movement analysis")

        self.right_before, self.before, self.now = behavior[-3:]

        # Extract Mario objects
        self.mario_now = model.get("player", self.now)
        self.mario_before = model.get("player", self.before)

        # Get positions
        self.pos_right_before = model.get_position(self.right_before)
        self.pos_before = model.get_position(self.before)
        self.pos_now = model.get_position(self.now)

        self.velocity = self.pos_before - self.pos_right_before
        self.actual_movement = self.pos_now - self.pos_before

        # Extract key states
        keys = model.get_pressed_keys(self.now)
        self.right_pressed = keys.get("right", False)
        self.left_pressed = keys.get("left", False)

    def debug(self):
        """Debug Mario's movement state."""
        debug(f"Mario: {self.pos_right_before} -> {self.pos_before} -> {self.pos_now}")
        debug(f"Velocity: {self.velocity}, Movement: {self.actual_movement}")
        debug(f"Keys: right={self.right_pressed}, left={self.left_pressed}")
        debug(
            f"Collision: before={self.model.has_collision(self.mario_before, self.before)}, now={self.model.has_collision(self.mario_now, self.now)}"
        )
        debug(
            f"Right touch: before={self.model.has_right_touch(self.mario_before, self.before)}, now={self.model.has_right_touch(self.mario_now, self.now)}"
        )
        debug(
            f"Left touch: before={self.model.has_left_touch(self.mario_before, self.before)}, now={self.model.has_left_touch(self.mario_now, self.now)}"
        )
        debug(
            f"Left boundary: before={self.model.level.is_at_left_boundary(self.mario_before)}, now={self.model.level.is_at_left_boundary(self.mario_now)}"
        )
        debug(
            f"Right boundary: before={self.model.level.is_at_right_boundary(self.mario_before)}, now={self.model.level.is_at_right_boundary(self.mario_now)}"
        )


class Movement(Model):
    """Mario movement model."""

    def __init__(self, game, level):
        super().__init__(game)
        self.level = level
        self.causal = CausalProperties(self)

    def expect(self, behavior):
        """Expect Mario to move correctly."""
        # Check if behavior has enough frames for movement analysis
        if not Behavior.valid(behavior):
            return

        # Create movement behavior analysis
        behavior = Behavior(self, behavior)
        behavior.debug()

        # Validate what Mario actually did
        self.causal.check_right_movement(behavior)
        self.causal.check_left_movement(behavior)
        self.causal.check_stayed_in_place(behavior)
