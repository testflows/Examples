from testflows.core import debug

from ..base import Model


class Behavior:
    """Encapsulates Mario's movement behavior extracted from behavior history states."""

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
        self.velocity_now = self.pos_now - self.pos_before
        self.actual_movement = self.pos_now - self.pos_before

        # Vertical (y-axis) positions and velocities
        self.pos_y_right_before = model.get_position(self.right_before, axis="y")
        self.pos_y_before = model.get_position(self.before, axis="y")
        self.pos_y_now = model.get_position(self.now, axis="y")

        self.vertical_velocity = self.pos_y_before - self.pos_y_right_before
        self.vertical_velocity_now = self.pos_y_now - self.pos_y_before
        self.actual_vertical_movement = self.pos_y_now - self.pos_y_before

        # Extract key states
        self.keys = model.get_pressed_keys(self.now)


class Propositions:
    """Atomic propositions for Mario's movement."""

    def __init__(self, model):
        self.model = model

    def right_pressed(self, keys):
        return keys.get("right", False)

    def left_pressed(self, keys):
        return keys.get("left", False)

    def jump_pressed(self, keys):
        return keys.get("jump", False)

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

    def past_left_boundary(self, mario_now):
        return self.model.level.is_past_left_boundary(mario_now)

    def past_right_boundary(self, mario_now):
        return self.model.level.is_past_right_boundary(mario_now)

    def on_the_ground(self, mario_now, now):
        """Check if Mario is on the ground (has bottom collision)."""
        return self.model.has_bottom_touch(mario_now, now)

    def stomped_enemy(self, mario, state):
        """Check if Mario has stomped an enemy."""
        return self.model.has_bottom_touch(
            mario, state, objects=self.model.stompable_enemy_objects
        )

    def in_the_air(self, mario_now, now):
        """Check if Mario is in the air (no bottom collision)."""
        return not self.on_the_ground(mario_now, now)

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

    def moved(self, actual_movement):
        return actual_movement != 0

    def stayed_in_place(self, actual_movement):
        return actual_movement == 0

    def moved_down(self, actual_vertical_movement):
        return actual_vertical_movement > 0

    def moved_up(self, actual_vertical_movement):
        return actual_vertical_movement < 0

    def stayed_in_the_air(self, actual_vertical_movement):
        return actual_vertical_movement == 0

    def stayed_in_the_air_or_bounced(self, actual_vertical_movement):
        return actual_vertical_movement <= 0

    def velocity_up(self, velocity):
        return velocity < 0

    def velocity_down(self, velocity):
        return velocity > 0

    def path_is_clear(self, mario_now, now, mario_before, before, direction):
        """Check if Mario's path is clear for movement in the given direction."""

        if direction == "right":
            return not self.right_touching(
                mario_now, now, mario_before, before
            ) and not self.at_right_boundary(mario_now)
        else:  # left
            return not self.left_touching(
                mario_now, now, mario_before, before
            ) and not self.at_left_boundary(mario_now)

    def has_right_direction(self, mario, state):
        return self.model.direction(state, self.in_the_air(mario, state)) == "right"

    def has_left_direction(self, mario, state):
        return self.model.direction(state, self.in_the_air(mario, state)) == "left"

    def stayed_still_too_long(self, stayed_still):
        return stayed_still > 20

    def exceeds_max_velocity(self, velocity):
        return abs(velocity) > 6

    def exceeds_max_vertical_velocity(self, velocity):
        return abs(velocity) > 11


class CausalProperties(Propositions):
    """Causal properties for Mario's movement."""

    def check_right_movement(self, behavior):
        """Check if Mario's right movement had a valid cause."""

        actual_movement = behavior.actual_movement
        velocity = behavior.velocity
        right_pressed = self.right_pressed(behavior.keys)

        if self.moved_right(actual_movement):
            self.model.assert_with_success(
                self.has_right_movement_cause(velocity, right_pressed),
                f"moved right because {f'velocity is {velocity}' if velocity > 0 else 'right key is pressed'}",
            )

    def check_left_movement(self, behavior):
        """Check if Mario's left movement had a valid cause."""

        actual_movement = behavior.actual_movement
        velocity = behavior.velocity
        left_pressed = self.left_pressed(behavior.keys)

        if self.moved_left(actual_movement):
            self.model.assert_with_success(
                self.has_left_movement_cause(velocity, left_pressed),
                f"moved left because {f'velocity is {velocity}' if velocity < 0 else 'left key is pressed'}",
            )

    def check_stayed_in_place(self, behavior):
        """Check if Mario staying in place had a valid cause."""

        actual_movement = behavior.actual_movement
        velocity = behavior.velocity

        right_pressed = self.right_pressed(behavior.keys)
        left_pressed = self.left_pressed(behavior.keys)

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

    def check_fall(self, behavior):
        """Check if Mario's fall (downward movement) has a valid cause."""

        actual_vertical_movement = behavior.actual_vertical_movement

        if self.moved_down(actual_vertical_movement):
            mario_before = behavior.mario_before
            before = behavior.before
            self.model.assert_with_success(
                not self.on_the_ground(mario_before, before),
                "fell because there was no ground support",
            )

    def check_stop_fall(self, behavior):
        """Check if stopped falling has a valid cause (landing)."""

        was_falling = self.velocity_down(behavior.vertical_velocity)
        now_vertical_movement = behavior.actual_vertical_movement

        if was_falling and self.stayed_in_the_air_or_bounced(now_vertical_movement):
            mario_now = behavior.mario_now
            now = behavior.now
            before = behavior.before
            mario_before = behavior.mario_before
            self.model.assert_with_success(
                self.on_the_ground(mario_now, now)
                or self.stomped_enemy(mario_before, before),
                "stopped falling because landed on support or stomped an enemy",
            )

    def check_jump(self, behavior):
        """Check if Mario's upward movement (jump) has a valid cause."""

        actual_vertical_movement = behavior.actual_vertical_movement
        vertical_velocity = behavior.vertical_velocity

        if self.moved_up(actual_vertical_movement):
            jump_pressed = self.jump_pressed(behavior.keys)
            mario_before = behavior.mario_before
            before = behavior.before
            self.model.assert_with_success(
                (jump_pressed and self.on_the_ground(mario_before, before))
                or self.stomped_enemy(mario_before, before)
                or self.velocity_up(vertical_velocity),
                "jumped because jump was pressed on ground or bounced off enemy or had upward velocity",
            )


class LivenessProperties(Propositions):
    """Liveness properties for Mario's movement."""

    def check_starts_moving(self, behavior, window=30):
        """Check if Mario eventually starts moving when keys are consistently pressed."""

        history = list(reversed(behavior.history[-window:]))
        stayed_still = 0

        # set current direction
        direction = self.model.direction(
            behavior.now, self.in_the_air(behavior.mario_now, behavior.now)
        )

        if direction is None:
            # no keys pressed
            return

        for now, before in zip(history[:-1], history[1:]):
            pos_before = self.model.get_position(before)
            pos_now = self.model.get_position(now)
            actual_movement = pos_now - pos_before

            mario_now = self.model.get("player", now)
            mario_before = self.model.get("player", before)

            # Mario started moving
            if self.moved(actual_movement):
                break

            # check if direction was changed
            if self.model.direction(now, self.in_the_air(mario_now, now)) != direction:
                break

            # check if path was blocked
            if not self.path_is_clear(mario_now, now, mario_before, before, direction):
                break

            stayed_still += 1

        if stayed_still < 1:
            return

        self.model.assert_with_success(
            not self.stayed_still_too_long(stayed_still),
            f"Mario started moving after {stayed_still} frames",
        )


class SafetyProperties(Propositions):
    """Safety properties for Mario's movement."""

    def check_does_not_move_past_left_boundary(self, behavior):
        """Check if Mario does not move past the boundary."""

        self.model.assert_with_success(
            not self.past_left_boundary(behavior.mario_now),
            f"Mario is within left boundary x={behavior.mario_now.box.x}, boundary={self.model.level.start_x}",
        )

    def check_does_not_move_past_right_boundary(self, behavior):
        """Check if Mario does not move past the boundary."""

        self.model.assert_with_success(
            not self.past_right_boundary(behavior.mario_now),
            f"Mario is within right boundary x={behavior.mario_now.box.x}, boundary={self.model.level.end_x - behavior.mario_now.box.w}",
        )

    def check_does_not_exceed_max_velocity(self, behavior):
        """Check if Mario does not exceed the maximum speed."""

        self.model.assert_with_success(
            not self.exceeds_max_velocity(behavior.velocity_now),
            f"Mario's velocity {behavior.velocity_now} is less than the maximum",
        )

    def check_does_not_exceed_max_vertical_velocity(self, behavior):
        """Check if Mario does not exceed the maximum vertical velocity."""

        self.model.assert_with_success(
            not self.exceeds_max_vertical_velocity(behavior.vertical_velocity_now),
            f"Mario's vertical velocity {behavior.vertical_velocity_now} is less than the maximum",
        )


class Movement(Model):
    """Mario movement model."""

    def __init__(self, game, level):
        super().__init__(game)
        self.level = level
        self.causal = CausalProperties(self)
        self.liveness = LivenessProperties(self)
        self.safety = SafetyProperties(self)

    def expect(self, behavior):
        """Expect Mario to move correctly."""
        # Check if behavior has enough frames for movement analysis
        if not Behavior.valid(behavior):
            return

        # Create movement behavior analysis
        behavior = Behavior(self, behavior)

        # Validate what Mario actually did
        self.causal.check_right_movement(behavior)
        self.causal.check_left_movement(behavior)
        self.causal.check_stayed_in_place(behavior)
        self.causal.check_fall(behavior)
        self.causal.check_stop_fall(behavior)
        self.causal.check_jump(behavior)

        # Validate what Mario should eventually do
        self.liveness.check_starts_moving(behavior)

        # Validate what Mario should never do
        self.safety.check_does_not_move_past_left_boundary(behavior)
        self.safety.check_does_not_move_past_right_boundary(behavior)
        self.safety.check_does_not_exceed_max_velocity(behavior)
        self.safety.check_does_not_exceed_max_vertical_velocity(behavior)
