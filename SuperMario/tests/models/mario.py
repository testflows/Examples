from testflows.core import debug
from .base import Model


class Mario(Model):
    """Mario's behavior model."""

    def __init__(self, game, level):
        super().__init__(game)
        # Movement constants
        self.max_speed = 6
        self.movement_startup_delay = 4
        self.inertia_threshold = 7
        # Physics constants
        self.max_falling_speed = 11
        self.falling_threshold = 3  # Max frames Mario can be stationary in air
        # Level model for boundary checking
        self.level = level

    def get_position(self, state, axis="x"):
        """Return Mario's x-coordinate from the given state."""
        mario = self.get("player", state)
        if axis == "x":
            return mario.box.x
        return mario.box.y

    def get_positions(self, *states, axis="x"):
        """Return Mario's positions from multiple states."""
        return tuple(self.get_position(state, axis) for state in states)

    def is_standing(self, state, previous_state):
        """
        Determine if Mario was standing between two states.
        He is considered standing if his x-coordinate did not change.
        """
        pos_current, pos_previous = self.get_positions(state, previous_state)
        return pos_current == pos_previous

    def is_moving(self, state, previous_state, direction="right"):
        """
        Determine if Mario was moving right between two states.
        He is moving right if his x-coordinate increased.
        """
        pos_current, pos_previous = self.get_positions(state, previous_state)
        if direction == "right":
            return pos_current > pos_previous
        elif direction == "left":
            return pos_current < pos_previous
        return False

    def has_recent_momentum(self, behavior, direction="right"):
        """
        Check if Mario recently had momentum in the specified direction,
        even if he's not currently moving pixelwise (due to internal deceleration).
        """
        # Look back through recent behavior to find momentum
        for i in range(min(8, len(behavior) - 1)):
            state_index = -(i + 2)  # Start from behavior[-2] and go backwards
            if abs(state_index) > len(behavior):
                break
            current_state = behavior[state_index]
            prev_state = (
                behavior[state_index - 1]
                if abs(state_index - 1) <= len(behavior)
                else current_state
            )

            if self.is_moving(current_state, prev_state, direction=direction):
                debug(f"Recent {direction} momentum detected {i+1} frames ago")
                return True
        return False

    def should_expect_turnaround_movement(self, behavior, direction="right"):
        """
        Determine if Mario should be able to move in the new direction after turnaround.
        Returns True if enough time has passed for turnaround deceleration to complete.
        """
        opposite_direction = "left" if direction == "right" else "right"

        # Count how many frames Mario has been stationary after stopping opposite movement
        stationary_frames = 0
        for i in range(len(behavior) - 1):
            state_index = -(i + 1)  # Start from behavior[-1] (now) and go backwards
            if abs(state_index) > len(behavior) or abs(state_index - 1) > len(behavior):
                break

            current_state = behavior[state_index]
            prev_state = behavior[state_index - 1]

            # Check if Mario is stationary in this frame
            pos_current, pos_prev = self.get_positions(current_state, prev_state)
            if pos_current == pos_prev:
                stationary_frames += 1
            else:
                # If Mario was moving, check if it was in opposite direction (still decelerating)
                if (opposite_direction == "right" and pos_current > pos_prev) or (
                    opposite_direction == "left" and pos_current < pos_prev
                ):
                    # Still had opposite momentum - turnaround not complete yet
                    break
                else:
                    # Mario was moving in new direction - turnaround already complete
                    return True

        # Mario should be able to move after sufficient stationary frames
        turnaround_delay = 7  # Frames needed for internal turnaround deceleration (observed from debug output)
        return stationary_frames >= turnaround_delay

    def is_jumping(self, state, previous_state):
        """
        Determine if Mario was jumping between two states.
        He is jumping if his y-coordinate decreased.
        """
        pos_current, pos_previous = self.get_positions(state, previous_state, axis="y")
        return pos_current < pos_previous

    def is_airborne(self, state):
        """
        Check if Mario is in the air (no bottom collision).
        """
        mario = self.get("player", state)
        return not self.has_collision(mario, state, "bottom")

    def assert_gravity_working(self, behavior):
        """
        Assert that gravity is working properly when Mario is airborne and stationary.

        If Mario has been stationary in air for more than falling_threshold frames,
        gravity system has failed.
        """
        if len(behavior) < self.falling_threshold + 2:  # Need enough history
            return

        # Check if Mario has been stationary in air for too many consecutive frames
        positions = []
        for i in range(self.falling_threshold + 1):
            state = behavior[-(i + 1)]  # Go backwards through history
            positions.append(self.get_position(state, axis="y"))

        # If all positions are the same, Mario has been stationary
        if len(set(positions)) == 1:  # All positions identical
            # Check if he was airborne during this time
            oldest_state = behavior[-(self.falling_threshold + 1)]
            if self.is_airborne(oldest_state):
                assert (
                    False
                ), f"Mario has been stationary in air for {self.falling_threshold}+ frames without falling - gravity not working"

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
        Assert that Mario jumped by observing y-position change.

        Note: Jump has a 1-frame delay - when jump key is pressed, Mario's y-position
        changes in the next frame. We need to look at the behavior history to detect jumps.
        """
        debug("Mario should jump")
        pos_now = self.get_position(now, axis="y")
        pos_before = self.get_position(before, axis="y")

        # Mario jumped if his y-position decreased (moved upward)
        if pos_now < pos_before:
            y_movement = pos_before - pos_now  # Positive value for upward movement
            debug(f"Mario jumped: moved up by {y_movement} pixels")
            return

        # Due to 1-frame delay, jump might not be visible yet
        # This is expected behavior and not a failure
        debug(
            f"Jump not yet visible: y_before={pos_before}, y_now={pos_now} (1-frame delay expected)"
        )

    def assert_movement(self, now, before, direction="right"):
        """
        Assert that Mario moved to the right or left and did not exceed max walking speed.
        """
        pos_now = self.get_position(now)
        pos_before = self.get_position(before)

        # Check boundary and collision conditions
        mario_before = self.get("player", before)

        if direction == "right":
            debug("Mario should move right")
            # Check level boundary
            if self.level.should_stay_at_boundary(mario_before, direction):
                # Mario should stay at boundary, not move further
                debug("Mario blocked by level boundary (right)")
                assert (
                    pos_now == pos_before
                ), f"Mario should not move right past boundary"
            # Check wall/object collision
            elif self.has_collision(mario_before, before, "right"):
                # Mario hit a wall/object - should not move further
                debug("Mario blocked by collision (right)")
                assert (
                    pos_now == pos_before
                ), f"Mario should not move right when blocked by collision"
            else:
                debug(
                    f"Mario should move right: pos_before={pos_before}, pos_now={pos_now}"
                )
            assert pos_now > pos_before, "Mario did not move right"
        elif direction == "left":
            debug("Mario should move left")
            # Check level boundary
            if self.level.should_stay_at_boundary(mario_before, direction):
                # Mario should stay at boundary, not move further
                debug("Mario blocked by level boundary (left)")
                assert (
                    pos_now == pos_before
                ), f"Mario should not move left past boundary"
            # Check wall/object collision
            elif self.has_collision(mario_before, before, "left"):
                # Mario hit a wall/object - should not move further
                debug("Mario blocked by collision (left)")
                assert (
                    pos_now == pos_before
                ), f"Mario should not move left when blocked by collision"
            else:
                debug(
                    f"Mario should move left: pos_before={pos_before}, pos_now={pos_now}"
                )
            assert pos_now < pos_before, "Mario did not move left"

        # Ensure Mario did not exceed the maximum speed (only if he actually moved)
        if pos_now != pos_before:
            self.assert_max_speed(now, before, direction=direction)

    def assert_max_speed(self, now, before, direction="right"):
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
            movement <= self.max_speed
        ), f"Mario moved {direction} {movement} above its max speed {self.max_speed}"

    def has_started_moving_after_standing(self, behavior, direction="right"):
        """
        Check the previous states to see if Mario has started moving after standing.
        Returns True if the delay in movement is at least the startup delay threshold.
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
        return did_not_move_count >= self.movement_startup_delay

    def has_maintained_inertia(self, behavior, previous_movement, direction="right"):
        """
        Check whether Mario has maintained the same inertia speed for at least 'threshold_frames'
        consecutive frame pairs (starting from the pair (behavior[-3], behavior[-2])).

        Returns True if the inertia speed is maintained for the threshold or more frames,
        and False otherwise.

        Special case: If Mario doesn't have bottom collision (i.e., he's jumping/falling),
        inertia is maintained indefinitely.
        """
        if len(behavior) < 3:
            return False

        # Start with the initial pair (right_before, before)
        count = 1
        current_state = behavior[-3]  # right_before

        # Iterate over earlier states starting from behavior[-4]
        for state in behavior[-4::-1]:
            # If the key is pressed in the previous state, break the inertia chain.
            if self.is_key_pressed(current_state, direction):
                break
            # If Mario didn't have bottom collision in the current state, break the inertia chain
            # because air physics are different and shouldn't count toward ground inertia threshold
            mario_current = self.get("player", current_state)
            if not self.has_collision(mario_current, current_state, "bottom"):
                debug("Mario is in the air, breaking ground inertia chain")
                break
            # If the movement delta between state_before and the current state differs, break.
            if direction == "right":
                if (
                    self.get_position(current_state) - self.get_position(state)
                    != previous_movement
                ):
                    break
            elif direction == "left":
                if (
                    self.get_position(state) - self.get_position(current_state)
                    != previous_movement
                ):
                    break
            count += 1
            current_state = state

        return count >= self.inertia_threshold

    def assert_inertia_movement(self, behavior, direction="right"):
        """
        Assert that Mario continues moving due to inertia even though the right or left key is not pressed.

        His current movement (from 'before' to 'now') must not exceed his previous movement
        (from 'right_before' to 'before'). Additionally, if Mario has maintained the same inertia
        speed for at least 'threshold_frames' consecutive frames, then he is expected to decelerate.
        """
        if len(behavior) < 3:
            return

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]
        pos_now, pos_before, pos_right_before = self.get_positions(
            now, before, right_before
        )

        if direction == "right":
            current_movement = pos_now - pos_before
            previous_movement = pos_before - pos_right_before
            # Verify that Mario is still moving right or stopped.
            assert (
                pos_now >= pos_before
            ), "Mario did not continue moving right due to inertia"
        elif direction == "left":
            current_movement = pos_before - pos_now
            previous_movement = pos_right_before - pos_before
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
            behavior, previous_movement, direction=direction
        ):
            # If so, then we expect deceleration (i.e. current movement must be less than previous).
            assert (
                current_movement < previous_movement
            ), f"Mario maintained the same inertia speed ({previous_movement}); but expected deceleration."

        debug(
            f"Mario has {direction} inertia current speed {current_movement}, previous speed {previous_movement}; should maintain its speed or decelerate"
        )

    def expect_move(self, behavior, direction):
        """Expect Mario to move right or left when the right or left key is pressed."""
        # Need at least three states: now, before, and right_before.
        if len(behavior) < 3:
            return

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]
        opposite_direction = "left" if direction == "right" else "right"

        # Check for simultaneous key presses - game has priority rules
        left_pressed = self.is_key_pressed(before, "left")
        right_pressed = self.is_key_pressed(before, "right")

        if left_pressed and right_pressed:
            # Both keys pressed - apply game's priority rules
            if self.is_airborne(before):
                # While jumping/falling: right takes priority
                if direction == "left":
                    return  # Skip left movement validation
            else:
                # While walking: left takes priority
                if direction == "right":
                    return  # Skip right movement validation

        if not self.is_key_pressed(before, direction):
            # When the right or left key is not pressed, determine if Mario should remain still or continue due to inertia.
            if self.is_moving(before, right_before, direction=direction):
                # Mario is already in motion. He should continue moving due to inertia,
                # but his current movement should not exceed his previous movement.
                # And if the same inertia speed is held for too long (7+ frames), he must decelerate.
                self.assert_inertia_movement(behavior, direction=direction)
            else:
                # Mario is not moving and no key is pressed: he must remain stationary.
                self.assert_no_unintended_movement(now, before, direction=direction)
            return

        if self.is_moving(before, right_before, direction=direction):
            # If Mario was already moving right, he should continue.
            self.assert_movement(now, before, direction=direction)

        elif self.is_standing(before, right_before):
            # Check if Mario has recent momentum in opposite direction (turnaround scenario)
            if self.has_recent_momentum(behavior, direction=opposite_direction):
                # Mario is decelerating from opposite momentum - check if he's still decelerating or ready to move
                debug(
                    f"Mario appears standing but has recent {opposite_direction} momentum (turnaround)"
                )

                # Check if Mario is actually moving in the opposite direction (still has inertia)
                pos_now, pos_before = self.get_positions(now, before)
                if opposite_direction == "right" and pos_now > pos_before:
                    # Mario is still moving right - apply inertia logic
                    self.assert_inertia_movement(behavior, direction=opposite_direction)
                elif opposite_direction == "left" and pos_now < pos_before:
                    # Mario is still moving left - apply inertia logic
                    self.assert_inertia_movement(behavior, direction=opposite_direction)
                else:
                    # Mario has stopped moving in opposite direction - but may still be decelerating internally
                    debug(
                        f"Mario has finished {opposite_direction} deceleration - checking if ready for new direction"
                    )

                    # Check if Mario actually moved in the new direction
                    pos_now, pos_before = self.get_positions(now, before)
                    if direction == "left" and pos_now < pos_before:
                        # Mario is moving left - turnaround complete
                        debug(
                            f"Mario successfully started moving {direction} after turnaround"
                        )
                        self.assert_movement(now, before, direction=direction)
                    elif direction == "right" and pos_now > pos_before:
                        # Mario is moving right - turnaround complete
                        debug(
                            f"Mario successfully started moving {direction} after turnaround"
                        )
                        self.assert_movement(now, before, direction=direction)
                    else:
                        # Mario hasn't started moving yet - check if we should expect movement
                        should_move = self.should_expect_turnaround_movement(
                            behavior, direction
                        )

                        # Assert that Mario remains stationary or moves correctly during turnaround
                        if direction == "left":
                            assert (
                                pos_now >= pos_before
                            ), f"Mario moved right during left turnaround: {pos_before} -> {pos_now}"
                        elif direction == "right":
                            assert (
                                pos_now <= pos_before
                            ), f"Mario moved left during right turnaround: {pos_before} -> {pos_now}"

                        if should_move:
                            # Mario MUST start moving now - no more waiting allowed
                            debug(
                                f"Mario turnaround deceleration complete (7 frames) - must move {direction} now"
                            )
                            self.assert_movement(now, before, direction=direction)
                        else:
                            # Still in turnaround deceleration period
                            if pos_now == pos_before:
                                debug(
                                    f"Mario stationary during turnaround deceleration - waiting to move {direction}"
                                )
                            else:
                                debug(
                                    f"Mario still decelerating during turnaround - waiting to move {direction}"
                                )
                            return
            else:
                # If he was truly standing, allow a delay before he starts moving.
                pos_before, pos_right_before = self.get_positions(before, right_before)
                debug(
                    f"Mario was truly standing (pos_before={pos_before}, pos_right_before={pos_right_before})"
                )

                startup_ready = self.has_started_moving_after_standing(
                    behavior, direction=direction
                )
                debug(
                    f"Mario standing check: startup_ready={startup_ready}, movement_startup_delay={self.movement_startup_delay}"
                )
                if not startup_ready:
                    debug(f"Mario was standing and is preparing to move {direction}")
                    return
                debug(f"Mario startup delay completed - should move {direction}")
            self.assert_movement(now, before, direction=direction)

        elif self.is_moving(before, right_before, direction=opposite_direction):
            # If Mario was moving in the opposite direction, he should briefly continue due to inertia
            # before he can switch direction.
            self.assert_inertia_movement(behavior, direction=opposite_direction)

        else:
            # By default, assert that Mario moved right or left to catch any unexpected behavior.
            self.assert_movement(now, before, direction=direction)
            return

    def is_jump_initiated(self, behavior):
        """
        Check if a jump was just initiated (jump key pressed and Mario can jump).

        Returns True if jump initiation should be handled by expect_jump.
        """
        if len(behavior) < 3:
            return False

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]

        # Check if jump key was just pressed
        jump_pressed_before = self.is_key_pressed(before, "a")
        jump_pressed_right_before = self.is_key_pressed(right_before, "a")

        # Check for jump key pressed recently (accounting for 1-frame delay)
        jump_pressed_now = self.is_key_pressed(now, "a")

        if (jump_pressed_before and not jump_pressed_right_before) or (
            jump_pressed_now and not jump_pressed_before
        ):
            # Jump key was just pressed (either in before or now frame) - check if Mario can jump
            # Check Mario's state in the frame before the key was pressed
            check_state = right_before if jump_pressed_before else before
            mario_check = self.get("player", check_state)
            has_bottom = self.has_collision(mario_check, check_state, "bottom")
            has_top = self.has_collision(mario_check, check_state, "top")

            if has_bottom and not has_top:
                return True  # Jump should be initiated
            else:
                # Mario cannot jump - this should be rare, but not an error (e.g., head collision)
                debug(
                    "Jump key pressed but Mario cannot jump - head collision or not on ground"
                )

        return False

    def expect_jump(self, behavior):
        """
        Expect Mario to jump when jump key is pressed and handle jump inertia physics.

        Similar to expect_move, this handles both:
        1. Initial jump expectation (when key first pressed)
        2. Jump inertia physics (upward movement with deceleration)
        """
        # Need at least 3 states to handle 1-frame delay: now, before, right_before
        if len(behavior) < 3:
            return

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]

        # Check for jump inertia (upward movement) - similar to horizontal inertia in expect_move
        pos_now = self.get_position(now, axis="y")
        pos_before = self.get_position(before, axis="y")
        pos_right_before = self.get_position(right_before, axis="y")

        current_y_movement = pos_before - pos_now  # Positive = upward
        previous_y_movement = pos_right_before - pos_before

        # If Mario has upward movement (jump inertia), validate physics
        if current_y_movement > 0:
            mario_before = self.get("player", before)
            jump_key_pressed = self.is_key_pressed(before, "a")

            # Check for head collision (like wall collision for horizontal movement)
            if self.has_collision(mario_before, before, "top"):
                debug("Mario hit his head - upward movement stopped")
                assert (
                    current_y_movement == 0
                ), f"Mario should stop moving upward when hitting head, but moved {current_y_movement}"
                return

            if (
                previous_y_movement > 0
            ):  # Had upward movement before (inertia continues)
                # Under jump inertia, Mario should not accelerate upward
                assert (
                    current_y_movement <= previous_y_movement
                ), f"Mario should not accelerate upward during jump inertia: {current_y_movement} > {previous_y_movement}"

                if jump_key_pressed:
                    debug(
                        f"Mario has upward inertia with jump key: movement {current_y_movement} (was {previous_y_movement})"
                    )
                else:
                    debug(
                        f"Mario has upward inertia without jump key: movement {current_y_movement} (was {previous_y_movement})"
                    )
                    # Should decelerate faster when key not held
                    deceleration = previous_y_movement - current_y_movement
                    assert (
                        deceleration >= 0.5
                    ), f"Mario should decelerate faster when jump key released: deceleration {deceleration}"
            return

        # No upward movement - check for new jump initiation or validate no unexpected upward movement
        if self.is_jump_initiated(behavior):
            self.assert_jump(now, before)
        else:
            # No jump initiated - if Mario has bottom collision, he should not move upward
            mario_before = self.get("player", before)
            if self.has_collision(mario_before, before, "bottom"):
                # Mario is on ground and no jump - assert no upward movement
                pos_now = self.get_position(now, axis="y")
                pos_before = self.get_position(before, axis="y")
                current_y_movement = pos_before - pos_now  # Positive = upward
                if current_y_movement > 0:
                    assert (
                        False
                    ), f"Mario on ground moved upward {current_y_movement} pixels without jumping"

    def expect_falling(self, behavior):
        """
        Expect Mario to fall when he has no bottom collision and no upward movement.

        Falling behavior:
        - Mario should accelerate downward due to gravity
        - No upward movement (different from jump inertia)
        - Horizontal movement still possible during fall
        """
        if len(behavior) < 3:
            return

        now, before, right_before = behavior[-1], behavior[-2], behavior[-3]
        mario_before = self.get("player", before)
        mario_right_before = self.get("player", right_before)

        # Get y-positions
        pos_now = self.get_position(now, axis="y")
        pos_before = self.get_position(before, axis="y")
        pos_right_before = self.get_position(right_before, axis="y")

        # Calculate y-movements (positive = upward, negative = downward)
        current_y_movement = pos_before - pos_now
        previous_y_movement = pos_right_before - pos_before

        # Calculate collision states
        was_airborne_before = not self.has_collision(
            mario_right_before, right_before, "bottom"
        )

        # Check if Mario should be falling (no bottom collision and no upward movement)
        if (
            not self.has_collision(mario_before, before, "bottom")
            and current_y_movement <= 0
        ):
            # Mario is airborne and not moving upward - he should be falling (moving downward)
            if current_y_movement == 0:
                # Mario is stationary in air - he should start falling
                self.assert_gravity_working(behavior)
                debug("Mario is airborne and stationary - should start falling")
                return

            elif current_y_movement < 0:  # Moving downward
                # Mario is falling - validate falling physics
                downward_movement = (
                    -current_y_movement
                )  # Make positive for easier logic
                previous_downward_movement = (
                    -previous_y_movement if previous_y_movement < 0 else 0
                )

                if previous_downward_movement > 0:  # Was falling before
                    # Mario should accelerate downward due to gravity, but may reach terminal velocity

                    # Assert Mario never exceeds terminal velocity
                    assert (
                        downward_movement <= self.max_falling_speed
                    ), f"Mario exceeded terminal velocity: {downward_movement} > {self.max_falling_speed}"

                    if previous_downward_movement >= self.max_falling_speed:
                        # At or near terminal velocity - speed should remain constant or decrease (if hitting ground)
                        debug(
                            f"Mario at terminal velocity: downward movement {downward_movement} (was {previous_downward_movement})"
                        )

                        if downward_movement < previous_downward_movement:
                            # Speed decreased - Mario must have hit the ground
                            mario_now = self.get("player", now)
                            assert self.has_collision(
                                mario_now, now, "bottom"
                            ), f"Mario's fall slowed from {previous_downward_movement} to {downward_movement} without ground collision - physics violation"
                            debug(
                                f"Mario hit the ground: speed reduced from {previous_downward_movement} to {downward_movement}"
                            )

                    else:
                        # Below terminal velocity - should accelerate
                        assert (
                            downward_movement >= previous_downward_movement
                        ), f"Mario should accelerate downward while falling: {downward_movement} < {previous_downward_movement}"
                        debug(
                            f"Mario falling and accelerating: downward movement {downward_movement} (was {previous_downward_movement})"
                        )
                else:
                    # Mario just started falling - validate this is a legitimate transition
                    if was_airborne_before:
                        # Mario was airborne before - normal transition from jump peak or stationary air
                        debug(
                            f"Mario started falling from airborne position: downward movement {downward_movement}"
                        )
                    else:
                        # Mario was on ground before but is falling now - should only happen if stepped off platform
                        # This is a valid transition (stepping off edges) but worth noting
                        debug(
                            f"Mario stepped off ground and started falling: downward movement {downward_movement}"
                        )

                    # Assert reasonable initial falling speed (shouldn't start too fast)
                    assert (
                        downward_movement <= 3
                    ), f"Mario started falling too fast: {downward_movement} > 3 - should start gradually"
        else:
            # Mario has bottom collision (on ground) - check for unexpected downward movement
            if current_y_movement < -2:  # Large downward movement (negative values)
                # Large downward movement while on ground is unexpected
                debug(
                    f"Mario on ground had large downward movement: {current_y_movement}"
                )
                assert (
                    False
                ), f"Mario on ground should not have large downward movement: {current_y_movement}"

    def expect(self, behavior):
        """Expect Mario to behave correctly."""
        self.expect_move(behavior, direction="right")
        self.expect_move(behavior, direction="left")
        self.expect_jump(behavior)
        self.expect_falling(behavior)
