from testflows.core import debug
from .base import Model


class Mario(Model):
    """Mario's behavior model."""

    def __init__(self, game):
        super().__init__(game)

    def get_position(self, state, axis="x"):
        """Return Mario's x-coordinate from the given state."""
        if axis == "x":
            return self.get_mario(state).box.x
        return self.get_mario(state).box.y

    def is_standing(self, state, previous_state):
        """
        Determine if Mario was standing between two states.
        He is considered standing if his x-coordinate did not change.
        """
        return self.get_position(state) == self.get_position(previous_state)

    def is_moving(self, state, previous_state, direction="right"):
        """
        Determine if Mario was moving right between two states.
        He is moving right if his x-coordinate increased.
        """
        if direction == "right":
            return self.get_position(state) > self.get_position(previous_state)
        elif direction == "left":
            return self.get_position(state) < self.get_position(previous_state)
        return False

    def is_jumping(self, state, previous_state):
        """
        Determine if Mario was jumping between two states.
        He is jumping if his y-coordinate decreased.
        """
        return self.get_position(state, axis="y") < self.get_position(
            previous_state, axis="y"
        )

    def assert_no_unintended_movement(self, now, before, direction="right"):
        """Assert that Mario did not move if the right or left key was not pressed."""
        pos_now = self.get_position(now)
        pos_before = self.get_position(before)
        if direction == "right":
            assert (
                pos_now <= pos_before
            ), f"Mario unexpectedly moved right {pos_now - pos_before}"
        elif direction == "left":
            assert (
                pos_now >= pos_before
            ), f"Mario unexpectedly moved left {pos_before - pos_now}"

    def assert_jump(self, now, before):
        """
        Assert that Mario jumped and his y-coordinate decreased.
        """
        debug("Mario should jump")
        pos_now = self.get_position(now, axis="y")
        pos_before = self.get_position(before, axis="y")
        assert pos_now < pos_before, "Mario did not jump"

    def assert_movement(self, now, before, max_speed=6, direction="right"):
        """
        Assert that Mario moved to the right or left and did not exceed max walking speed.
        """
        pos_now = self.get_position(now)
        pos_before = self.get_position(before)
        if direction == "right":
            debug("Mario should move right")
            assert pos_now > pos_before, "Mario did not move right"
        elif direction == "left":
            debug("Mario should move left")
            assert pos_now < pos_before, "Mario did not move left"
        # Ensure Mario did not exceed the maximum speed.
        self.assert_max_speed(now, before, max_speed=max_speed, direction=direction)

    def assert_max_speed(self, now, before, max_speed, direction="right"):
        """
        Assert that Mario did not exceed the maximum speed.
        """
        pos_now = self.get_position(now)
        pos_before = self.get_position(before)
        if direction == "right":
            movement = pos_now - pos_before
            debug(f"Mario moved right by {movement}")
        elif direction == "left":
            movement = pos_before - pos_now
            debug(f"Mario moved left by {movement}")
        assert (
            movement <= max_speed
        ), f"Mario moved {direction} {movement} above its max speed {max_speed}"

    def has_started_moving_after_standing(
        self, behavior, threshold=4, direction="right"
    ):
        """
        Check the previous states to see if Mario has started moving after standing.
        Returns True if the delay in movement is at least the threshold.
        """
        did_not_move_count = 1
        # 'right_before' is the state 3 steps back in the behavior list.
        state_before = behavior[-3]
        for state in behavior[-4::-1]:
            # If Mario was not standing in this state, break.
            if self.get_position(state) != self.get_position(state_before):
                break
            # If the key wasn't pressed, no need to wait longer.
            if not self.is_key_pressed(state_before, direction):
                break
            did_not_move_count += 1
            state_before = state
        return did_not_move_count >= threshold

    def has_maintained_inertia(
        self, behavior, previous_movement, threshold_frames=7, direction="right"
    ):
        """
        Check whether Mario has maintained the same inertia speed for at least 'threshold_frames'
        consecutive frame pairs (starting from the pair (behavior[-3], behavior[-2])).

        Returns True if the inertia speed is maintained for the threshold or more frames,
        and False otherwise.
        """
        # Start with the initial pair (right_before, before)
        count = 1
        state_before = behavior[-3]  # right_before

        # Iterate over earlier states starting from behavior[-4]
        for state in behavior[-4::-1]:
            # If the key is pressed in the previous state, break the inertia chain.
            if self.is_key_pressed(state_before, direction):
                break
            # If the movement delta between state_before and the current state differs, break.
            if direction == "right":
                if (
                    self.get_position(state_before) - self.get_position(state)
                    != previous_movement
                ):
                    break
            elif direction == "left":
                if (
                    self.get_position(state) - self.get_position(state_before)
                    != previous_movement
                ):
                    break
            count += 1
            state_before = state

        return count >= threshold_frames

    def assert_inertia_movement(self, behavior, threshold=7, direction="right"):
        """
        Assert that Mario continues moving due to inertia even though the right or left key is not pressed.

        His current movement (from 'before' to 'now') must not exceed his previous movement
        (from 'right_before' to 'before'). Additionally, if Mario has maintained the same inertia
        speed for at least 'threshold_frames' consecutive frames, then he is expected to decelerate.

        The behavior list is expected to have at least 3 states:
          - behavior[-1] is "now"
          - behavior[-2] is "before"
          - behavior[-3] is "right_before"
        """
        if len(behavior) < 3:
            return

        now = behavior[-1]
        before = behavior[-2]
        right_before = behavior[-3]

        pos_now = self.get_position(now)
        pos_before = self.get_position(before)
        pos_right_before = self.get_position(right_before)

        if direction == "right":
            current_movement = pos_now - pos_before
            previous_movement = pos_before - pos_right_before
        elif direction == "left":
            current_movement = pos_before - pos_now
            previous_movement = pos_right_before - pos_before

        if direction == "right":
            # Verify that Mario is still moving right or stopped.
            assert (
                pos_now >= pos_before
            ), "Mario did not continue moving right due to inertia"
        elif direction == "left":
            # Verify that Mario is still moving left or stopped.
            assert (
                pos_now <= pos_before
            ), "Mario did not continue moving left due to inertia"

        # Under inertia, Mario should not accelerate.
        assert (
            current_movement <= previous_movement
        ), f"Mario should not accelerate with {direction} inertia: {current_movement}, previous {previous_movement}"

        # Check if the same inertia speed should start decreasing.
        if self.has_maintained_inertia(
            behavior, previous_movement, threshold, direction=direction
        ):
            # If so, then we expect deceleration (i.e. current movement must be less than previous).
            assert (
                current_movement < previous_movement
            ), f"Mario maintained the same inertia speed ({previous_movement}) for {threshold} frames; expected deceleration."

        debug(
            f"Mario has {direction} inertia current speed {current_movement}, previous speed {previous_movement}"
        )

    def expect_move(self, behavior, direction):
        """Expect Mario to move right or left when the right or left key is pressed."""
        # Need at least three states: now, before, and right_before.
        if len(behavior) < 3:
            return

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]

        if not self.is_key_pressed(before, direction):
            # When the right or left key is not pressed, determine if Mario should remain still or continue due to inertia.
            if self.is_moving(before, right_before, direction=direction):
                # Mario is already in motion. He should continue moving due to inertia,
                # but his current movement should not exceed his previous movement.
                # And if the same inertia speed is held for too long (7+ frames), he must decelerate.
                self.assert_inertia_movement(behavior, threshold=7, direction=direction)
            else:
                # Mario is not moving and no key is pressed: he must remain stationary.
                self.assert_no_unintended_movement(now, before, direction=direction)
            return

        if self.is_moving(before, right_before, direction=direction):
            # If Mario was already moving right, he should continue.
            self.assert_movement(now, before, direction=direction)

        elif self.is_standing(before, right_before):
            # If he was standing, allow a delay before he starts moving.
            if not self.has_started_moving_after_standing(
                behavior, threshold=4, direction=direction
            ):
                debug(f"Mario was standing and is preparing to move {direction}")
                return
            self.assert_movement(now, before, direction=direction)

        elif self.is_moving(
            before, right_before, direction="left" if direction == "right" else "right"
        ):
            # If Mario was moving in the opposite direction, he should briefly continue due to inertia
            # before he can switch direction.
            self.assert_inertia_movement(
                behavior,
                threshold=7,
                direction="left" if direction == "right" else "right",
            )

        else:
            # By default, assert that Mario moved right or left to catch any unexpected behavior.
            self.assert_movement(now, before, direction=direction)
            return

    def expect_jump(self, behavior):
        """Expect Mario to jump when jump key is pressed."""
        # Need at least three states: now, before, and right_before.
        if len(behavior) < 3:
            return

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]

        mario_before = self.get_mario(before)

        if self.has_collision(
            mario_before, before, "bottom", objects=["box", "collider"]
        ):
            if not self.has_collision(
                mario_before, before, "top", objects=["box", "collider"]
            ):
                if self.is_key_pressed(now, "a"):
                    # If Mario is standing on a solid object, has room at the top, and the jump key is pressed, Mario should jump.
                    self.assert_jump(now, before)

    def expect(self, behavior):
        """Expect Mario to behave correctly."""
        self.expect_move(behavior, direction="right")
        self.expect_move(behavior, direction="left")
        self.expect_jump(behavior)
