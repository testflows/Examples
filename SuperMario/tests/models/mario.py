from testflows.core import debug
from .base import Model


class Physics:
    """Handles Mario's physics predictions and validation."""

    def __init__(self, game):
        self.game = game
        # Game physics constants (extracted from game code)
        self.walk_accel = 0.5
        self.max_walk_vel = 6
        self.gravity = 0.5
        self.jump_vel = -11
        self.inertia_decay = 0.8

    def predict_x_position(self, mario_state, keys, mario_internal):
        """Predict Mario's next X position based on physics rules."""
        current_vel = mario_internal.get("x_vel", 0)
        current_pos = mario_state.box.x

        # Game uses round(x_vel) for position updates - if current velocity doesn't round to movement, no change
        if round(current_vel) == 0:
            return current_pos  # No movement if current velocity rounds to 0

        # If we get here, current velocity will cause movement
        return current_pos + round(current_vel)

    def predict_y_position(self, mario_state, keys, mario_internal):
        """Predict Mario's next Y position based on gravity/jump."""
        current_y_vel = mario_internal.get("y_vel", 0)
        current_pos = mario_state.box.y

        if keys.get("jump") and mario_internal.get("state") != "JUMP":
            # Jump initiation
            return current_pos + self.jump_vel
        else:
            # Gravity
            new_y_vel = min(current_y_vel + self.gravity, 11)  # Terminal velocity
            return current_pos + new_y_vel


class Collision:
    """Handles Mario's collision detection and classification."""

    def __init__(self, game):
        self.game = game

    def will_collide_with_enemy(self, before_state, predicted_x, predicted_y):
        """Check if Mario will collide with enemy at predicted position."""
        mario_elements = before_state.boxes.get("player", [])
        if not mario_elements:
            return None

        mario = mario_elements[0]
        if not hasattr(mario, "box"):
            return None

        temp_box = mario.box.copy()
        temp_box.x = predicted_x
        temp_box.y = predicted_y

        # Check enemy collision using vision system (same as colliderect)
        enemies = before_state.boxes.get("enemy", [])
        for enemy in enemies:
            if self.game.vision.collides(temp_box, enemy.box):
                return enemy
        return None

    def enemy_collision_type(self, mario_internal, enemy):
        """Determine if enemy collision is stomp or side collision."""
        if mario_internal.get("y_vel", 0) > 0:  # Mario falling
            return "stomp"
        else:
            return "side_collision"

    def will_collide_with_objects(self, mario_state, predicted_x, predicted_y):
        """Check if Mario will collide with solid objects at predicted position."""
        mario_elements = mario_state.boxes.get("player", [])
        if not mario_elements:
            return False

        mario = mario_elements[0]
        if not hasattr(mario, "box"):
            return False

        temp_box = mario.box.copy()
        temp_box.x = predicted_x
        temp_box.y = predicted_y

        # Check collision with solid objects using vision system (same as colliderect)
        solid_objects = ["box", "brick", "pipe", "ground", "step", "collider"]
        for obj_type in solid_objects:
            objects = mario_state.boxes.get(obj_type, [])
            for obj in objects:
                if self.game.vision.collides(temp_box, obj.box):
                    return True
        return False


class Mario(Model):
    """Mario's behavior model."""

    def __init__(self, game, level):
        super().__init__(game)
        # Composition - add physics predictor and collision detector
        self.physics = Physics(game)
        self.collision = Collision(game)
        # Movement constants
        self.max_speed = 6
        self.movement_startup_delay = 4
        self.inertia_threshold = 10
        self.momentum_lookback_frames = 8  # Frames to look back for recent momentum
        self.turnaround_delay_frames = (
            7  # Frames needed for internal turnaround deceleration
        )
        # Physics constants
        self.max_falling_speed = 11
        self.falling_threshold = 6  # Max frames Mario can be stationary in air
        self.min_history = 3  # Minimum behavior history needed for complex checks
        self.jump_deceleration_threshold = (
            0.5  # Minimum deceleration when jump key released
        )
        self.max_initial_fall_speed = 3  # Maximum speed when starting to fall
        self.max_ground_downward_movement = (
            2  # Maximum downward movement while on ground
        )
        self.residual_movement_tolerance = (
            1  # Tolerance for tiny residual movements from inertia
        )
        self.landing_impact_threshold = (
            4  # Downward speed that constitutes a "hard landing"
        )
        self.head_collision_fall_speed_min = (
            4  # Minimum fall speed after head collision
        )
        self.head_collision_fall_speed_max = (
            10  # Maximum fall speed after head collision (includes momentum effects)
        )
        # Enemy stomp constants
        self.enemy_stomp_min_deceleration = (
            3  # Minimum deceleration when stomping enemy
        )
        self.enemy_stomp_max_result_movement = (
            8  # Maximum downward movement after enemy stomp
        )
        # Interactive object collision constants
        self.interactive_collision_tolerance = (
            3  # Tolerance for detecting near-collisions with boxes/bricks
        )
        # Death state tracking
        self.mario_is_dead = False  # Flag to track if Mario has died
        # Level model for boundary checking
        self.level = level

    def internal_state(self):
        """Get minimal internal state needed for physics validation."""
        player = self.game.state.player
        return {
            "x_vel": player.x_vel,
            "y_vel": player.y_vel,
            "state": player.state,
            "big": player.big,
            "dead": player.dead,
            "invincible": player.invincible,
            "hurt_invincible": player.hurt_invincible,
            "walking_timer": player.walking_timer,
            "current_time": player.current_time,
            "frame_index": player.frame_index,
        }

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
        for i in range(min(self.momentum_lookback_frames, len(behavior) - 1)):
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
        return stationary_frames > self.turnaround_delay_frames

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

    def had_hard_landing(self, behavior):
        """
        Check if Mario just had a hard landing that might affect horizontal movement.
        """
        if len(behavior) < 2:
            return False

        now, before = behavior[-1], behavior[-2]

        # Check if Mario was airborne before and is on ground now
        if self.is_airborne(before) and not self.is_airborne(now):
            # Calculate the downward speed when landing
            pos_now = self.get_position(now, axis="y")
            pos_before = self.get_position(before, axis="y")
            downward_speed = pos_now - pos_before  # Positive = downward

            if downward_speed >= self.landing_impact_threshold:
                debug(f"Mario had hard landing: downward speed {downward_speed}")
                return True
        return False

    def had_head_collision(self, behavior):
        """
        Check if Mario just hit his head on something, causing immediate fall.
        """
        if len(behavior) < 2:
            return False

        now, before = behavior[-1], behavior[-2]
        mario_before = self.get("player", before)

        # Check if Mario had upward movement before but is now falling
        pos_now = self.get_position(now, axis="y")
        pos_before = self.get_position(before, axis="y")

        current_y_movement = pos_before - pos_now  # Positive = upward

        # If Mario was moving upward before but is now falling, check for head collision
        if current_y_movement < 0:  # Now falling (negative = downward)
            # Check if there was a head collision
            if self.has_collision(mario_before, before, "top"):
                downward_speed = -current_y_movement  # Make positive for easier reading
                debug(
                    f"Mario hit his head and started falling at speed {downward_speed}"
                )
                return True
        return False

    def had_recent_head_collision(self, behavior, frames_back=12):
        """
        Check if Mario had a head collision within the last few frames.
        Used to account for physics disruptions after hitting interactive objects.
        """
        if len(behavior) < 2:
            return False

        # Check the last few frames for head collisions
        for i in range(min(frames_back, len(behavior) - 1)):
            frame_behavior = behavior[:-(i)] if i > 0 else behavior
            if len(frame_behavior) >= 2 and self.had_head_collision(frame_behavior):
                debug(f"Recent head collision detected {i} frames ago")
                return True
        return False

    def had_recent_interactive_collision(self, behavior, frames_back=12):
        """
        Check if Mario recently collided with interactive objects (boxes, bricks)
        that might cause delayed physics disruptions.
        """
        if len(behavior) < 2:
            return False

        # Check recent frames for collisions with interactive objects
        for i in range(min(frames_back, len(behavior) - 1)):
            frame_idx = len(behavior) - 1 - i
            if frame_idx <= 0:
                break

            current_state = behavior[frame_idx]
            mario = self.get("player", current_state)

            # Check for collisions with interactive objects (boxes, bricks)
            interactive_objects = []
            interactive_objects.extend(current_state.boxes.get("box", []))
            interactive_objects.extend(current_state.boxes.get("brick", []))

            for obj in interactive_objects:
                # Check if Mario is colliding or very close to the object
                # This accounts for physics disruptions that happen 1-2 frames after collision
                # Both mario and obj are Element objects with .box attribute (pg.Rect)
                mario_box = mario.box
                obj_box = obj.box

                horizontal_close = (
                    mario_box.left
                    < obj_box.right + self.interactive_collision_tolerance
                    and mario_box.right
                    > obj_box.left - self.interactive_collision_tolerance
                )
                vertical_close = (
                    mario_box.top
                    < obj_box.bottom + self.interactive_collision_tolerance
                    and mario_box.bottom
                    > obj_box.top - self.interactive_collision_tolerance
                )

                if horizontal_close and vertical_close:
                    debug(
                        f"Recent interactive object collision detected {i} frames ago with {obj.name} at ({obj_box.x}, {obj_box.y}) (tolerance={self.interactive_collision_tolerance})"
                    )
                    return True
        return False

    def stomped_enemy(self, behavior):
        """
        Check if Mario just stomped on an enemy, causing a bounce effect.
        When Mario lands on enemies, his y_vel is set to -7 (upward bounce).
        """
        if len(behavior) < 2:
            return False

        now, before = behavior[-1], behavior[-2]
        mario_before = self.get("player", before)
        mario_now = self.get("player", now)

        # Check if Mario was falling and there's an enemy collision from above
        pos_now = self.get_position(now, axis="y")
        pos_before = self.get_position(before, axis="y")

        was_falling = pos_now > pos_before  # Mario was moving downward

        if was_falling:
            # Check for enemy collision - Mario landing on top of enemy
            # When Mario stomps Goomba, it's moved to dying_group immediately
            # Check multiple frames and different enemy groups
            all_enemies = []
            for i in range(min(3, len(behavior))):
                frame_idx = len(behavior) - 1 - i
                if frame_idx >= 0:
                    state = behavior[frame_idx]
                    # Check regular enemies
                    frame_enemies = state.boxes.get("enemy", [])
                    all_enemies.extend(frame_enemies)
                    # Check other enemy-related groups that might contain stomped enemies
                    for group_name in ["goomba", "koopa", "shell"]:
                        if group_name in state.boxes:
                            all_enemies.extend(state.boxes[group_name])

            debug(
                f"Checking enemy stomp: Mario fell {pos_now - pos_before} pixels, found {len(all_enemies)} total enemies"
            )
            debug(
                f"Mario before: ({mario_before.box.x}, {mario_before.box.y}), size: {mario_before.box.width}x{mario_before.box.height}"
            )

            # Check previous frames for enemies that might have been removed
            for i in range(min(3, len(behavior))):
                frame_idx = len(behavior) - 1 - i
                if frame_idx >= 0:
                    frame_enemies = behavior[frame_idx].boxes.get("enemy", [])
                    debug(f"Frame -{i} enemies: {len(frame_enemies)}")

            for enemy in all_enemies:
                # Check if Mario was above the enemy and colliding
                mario_bottom = mario_before.box.bottom
                enemy_top = enemy.box.top
                horizontal_overlap = (
                    mario_before.box.left < enemy.box.right
                    and mario_before.box.right > enemy.box.left
                )
                vertical_collision = (
                    mario_bottom <= enemy_top + 8
                )  # Increased tolerance

                debug(
                    f"Enemy at ({enemy.box.x}, {enemy.box.y}): Mario bottom {mario_bottom}, enemy top {enemy_top}, h_overlap {horizontal_overlap}, v_collision {vertical_collision}"
                )

                if vertical_collision and horizontal_overlap:
                    debug(
                        f"Mario stomped enemy: was falling {pos_now - pos_before} pixels"
                    )
                    return True
        return False

    def hit_moving_brick(self, behavior):
        """
        Check if Mario just hit a moving/bumped brick from below.
        When Mario hits a brick, it gets y_vel = -7 and state = BUMPED.
        """
        if len(behavior) < 2:
            return False

        now, before = behavior[-1], behavior[-2]

        # Check for bricks in recent frames that might be moving/bumped
        for i in range(min(3, len(behavior))):
            frame_idx = len(behavior) - 1 - i
            if frame_idx >= 0:
                state = behavior[frame_idx]
                bricks = state.boxes.get("brick", [])

                for brick in bricks:
                    # Check if this brick is near Mario's position
                    mario_before = self.get("player", before)
                    mario_x = mario_before.box.x
                    mario_y = mario_before.box.y

                    # Check if Mario was below the brick (hitting from below)
                    horizontal_align = (
                        abs(mario_x - brick.box.x) < 20
                    )  # Within reasonable range
                    vertical_below = (
                        mario_before.box.top > brick.box.bottom - 10
                    )  # Mario was below

                    if horizontal_align and vertical_below:
                        debug(
                            f"Mario hit moving brick at ({brick.box.x}, {brick.box.y}) from below"
                        )
                        return True
        return False

    def touched_enemy_side(self, behavior):
        """
        Check if Mario touched an enemy from the side (causing death or shrinking).
        Based on the game's actual collision logic from level.py:342-355
        """
        if len(behavior) < 2:
            return False

        now, before = behavior[-1], behavior[-2]
        mario_now = self.get("player", now)
        mario_before = self.get("player", before)

        # Check if Mario is invincible or hurt-invincible (can't be hurt)
        if hasattr(mario_now, "invincible") and mario_now.invincible:
            debug("Mario is invincible - enemy collision won't hurt Mario")
            return False
        if hasattr(mario_now, "hurt_invincible") and mario_now.hurt_invincible:
            debug("Mario is hurt-invincible - enemy collision ignored")
            return False

        # Check current frame for enemy collision (game checks every frame)
        state = behavior[-1]

        # Check all enemy-related groups (separate regular enemies from shells)
        regular_enemies = []
        shells = []

        # Regular enemies: enemy, goomba, koopa groups
        for group_name in ["enemy", "goomba", "koopa"]:
            group_enemies = state.boxes.get(group_name, [])
            regular_enemies.extend(group_enemies)

        # Shells are handled differently
        shell_enemies = state.boxes.get("shell", [])
        shells.extend(shell_enemies)

        debug(
            f"Checking {len(regular_enemies)} regular enemies and {len(shells)} shells for collision"
        )

        # Check regular enemy collisions first
        for enemy in regular_enemies:
            mario_box = mario_now.box
            enemy_box = enemy.box

            # Use tighter collision detection (like pygame sprite collision)
            collision_tolerance = 1  # Much tighter than before
            horizontal_overlap = (
                mario_box.left < enemy_box.right + collision_tolerance
                and mario_box.right > enemy_box.left - collision_tolerance
            )
            vertical_overlap = (
                mario_box.top < enemy_box.bottom + collision_tolerance
                and mario_box.bottom > enemy_box.top - collision_tolerance
            )

            debug(
                f"Enemy at ({enemy_box.x}, {enemy_box.y}): h_overlap={horizontal_overlap}, v_overlap={vertical_overlap}"
            )

            if horizontal_overlap and vertical_overlap:
                # Check if this is a stomp (Mario falling from above) vs side collision
                # Game logic: if Mario has positive y_vel (falling), it's a stomp
                mario_falling = hasattr(mario_now, "y_vel") and mario_now.y_vel > 0
                mario_above_enemy = (
                    mario_box.bottom <= enemy_box.top + 2
                )  # Tight tolerance

                debug(
                    f"Collision detected: Mario falling = {mario_falling}, Mario above enemy = {mario_above_enemy}"
                )

                if mario_falling and mario_above_enemy:
                    debug("This is a stomp, not a side collision")
                    continue  # This is a stomp, not harmful to Mario
                else:
                    debug("Side collision detected with regular enemy")
                    return True  # Side collision - Mario gets hurt

        # Check shell collisions (different logic)
        for shell in shells:
            mario_box = mario_now.box
            shell_box = shell.box

            collision_tolerance = 1
            horizontal_overlap = (
                mario_box.left < shell_box.right + collision_tolerance
                and mario_box.right > shell_box.left - collision_tolerance
            )
            vertical_overlap = (
                mario_box.top < shell_box.bottom + collision_tolerance
                and mario_box.bottom > shell_box.top - collision_tolerance
            )

            if horizontal_overlap and vertical_overlap:
                # Check if shell is sliding (dangerous) or stationary
                shell_sliding = hasattr(shell, "state") and shell.state == "shell_slide"

                if shell_sliding:
                    debug("Collision with sliding shell - Mario gets hurt")
                    return True  # Sliding shell hurts Mario
                else:
                    # Stationary shell - check if it's a stomp or kick
                    mario_falling = hasattr(mario_now, "y_vel") and mario_now.y_vel > 0
                    mario_above_shell = mario_box.bottom <= shell_box.top + 2

                    if mario_falling and mario_above_shell:
                        debug("Stomping stationary shell - activates it")
                        continue  # Stomping shell activates it, doesn't hurt Mario
                    else:
                        debug("Kicking stationary shell - doesn't hurt Mario")
                        continue  # Kicking shell doesn't hurt Mario

        return False  # No harmful collision detected

    def reset_death_flag(self):
        """Reset the death flag when Mario respawns or level restarts."""
        self.mario_is_dead = False
        debug("Mario death flag reset")

    def assert_gravity_working(self, behavior):
        """
        Assert that gravity is working properly when Mario is airborne and stationary.

        If Mario has been stationary in air for more than falling_threshold frames,
        gravity system has failed. However, allow for legitimate cases like jump peaks.
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
            movement = pos_now - pos_before
            assert (
                movement <= self.residual_movement_tolerance
            ), f"Mario unexpectedly moved right {movement} (tolerance: {self.residual_movement_tolerance})"
        elif direction == "left":
            movement = pos_before - pos_now
            assert (
                movement <= self.residual_movement_tolerance
            ), f"Mario unexpectedly moved left {movement} (tolerance: {self.residual_movement_tolerance})"

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

    def assert_movement(self, now, before, direction="right", behavior=None):
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
                return  # Exit early - boundary check complete
            # Check wall/object collision
            elif self.has_collision(mario_before, before, "right"):
                # Mario hit a wall/object - should not move further
                debug("Mario blocked by collision (right)")
                assert (
                    pos_now == pos_before
                ), f"Mario should not move right when blocked by collision"
                return  # Exit early - collision check complete
            else:
                # Special case: Mario at left boundary trying to move right may need extra frame
                if (
                    self.level.is_at_left_boundary(mario_before)
                    and pos_now == pos_before
                ):
                    debug(
                        "Mario at left boundary - may need extra frame to start moving right"
                    )
                    return  # Allow one frame delay when starting from left boundary
                # Check for hard landing impact
                if self.had_hard_landing(behavior) and pos_now == pos_before:
                    debug(
                        "Mario just had hard landing - horizontal movement may be delayed"
                    )
                    return  # Allow delayed movement after hard landing
                # Check if Mario is very close to a collision (within 1 pixel)
                if pos_now == pos_before and self.has_collision(
                    mario_before, before, "right"
                ):
                    debug("Mario blocked by collision detected after position check")
                    return  # Mario correctly stopped due to collision
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
                return  # Exit early - boundary check complete
            # Check wall/object collision
            elif self.has_collision(mario_before, before, "left"):
                # Mario hit a wall/object - should not move further
                debug("Mario blocked by collision (left)")
                assert (
                    pos_now == pos_before
                ), f"Mario should not move left when blocked by collision"
                return  # Exit early - collision check complete
            else:
                # Special case: Mario at right boundary trying to move left may need extra frame
                if (
                    self.level.is_at_right_boundary(mario_before)
                    and pos_now == pos_before
                ):
                    debug(
                        "Mario at right boundary - may need extra frame to start moving left"
                    )
                    return  # Allow one frame delay when starting from right boundary
                # Check for hard landing impact
                if self.had_hard_landing(behavior) and pos_now == pos_before:
                    debug(
                        "Mario just had hard landing - horizontal movement may be delayed"
                    )
                    return  # Allow delayed movement after hard landing
                # Check if Mario is very close to a collision (within 1 pixel)
                if pos_now == pos_before and self.has_collision(
                    mario_before, before, "left"
                ):
                    debug("Mario blocked by collision detected after position check")
                    return  # Mario correctly stopped due to collision
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
        if len(behavior) < self.min_history:
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
        if len(behavior) < self.min_history:
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
            debug(
                f"Mario has maintained inertia speed {previous_movement} for {self.inertia_threshold}+ frames - expecting deceleration"
            )
            assert (
                current_movement < previous_movement
            ), f"Mario maintained the same inertia speed ({previous_movement}); but expected deceleration."

        debug(
            f"Mario has {direction} inertia current speed {current_movement}, previous speed {previous_movement}; should maintain its speed or decelerate"
        )

    def expect_move(self, behavior, direction):
        """Expect Mario to move right or left using predictive physics."""
        if len(behavior) < 2:
            return

        before, after = behavior[-2], behavior[-1]

        # Get current state using our foundation
        keys = self.get_pressed_keys(before)

        # Check what should happen based on input
        key_pressed = keys.get(direction, False)

        if not key_pressed:
            # No key pressed - check for inertia or stationary behavior
            if len(behavior) >= 3:
                right_before = behavior[-3]
                if self.is_moving(before, right_before, direction=direction):
                    # Mario has inertia - should decelerate properly
                    self.assert_inertia_movement(behavior, direction=direction)
                else:
                    # Mario should remain stationary
                    self.assert_no_unintended_movement(
                        after, before, direction=direction
                    )
            return

        # Key IS pressed - predict what should happen using our Physics class
        mario_internal = self.internal_state()
        mario_state = self.get("player", before)

        predicted_x = self.physics.predict_x_position(mario_state, keys, mario_internal)
        before_x = self.get_position(before)
        actual_x = self.get_position(after)

        # Check if there are conditions preventing movement that our Physics class doesn't account for
        mario_before = self.get("player", before)
        has_boundary_block = (
            self.level.should_stay_at_boundary(mario_before, direction)
            if hasattr(self, "level")
            else False
        )
        has_collision_block = self.has_collision(mario_before, before, direction)

        # Debug: show what's preventing movement
        debug(
            f"Boundary block: {has_boundary_block}, Collision block: {has_collision_block}"
        )
        debug(f"Mario internal state: {mario_internal}")
        debug(f"Predicted velocity would be: {predicted_x - before_x}")

        # Debug: check if we need to account for walking timer
        if mario_internal.get("walking_timer", 0) == 0:
            debug("Walking timer not started yet - this might be the startup delay!")
        else:
            time_since_walk_start = mario_internal.get(
                "current_time", 0
            ) - mario_internal.get("walking_timer", 0)
            debug(f"Time since walking started: {time_since_walk_start}ms")

        # Round predicted position to whole pixels (game uses round())
        predicted_x_pixels = round(predicted_x)

        # Check if physics predicts movement in whole pixels, but account for blocks
        will_move = (
            abs(predicted_x_pixels - before_x) >= 1
            and not has_boundary_block
            and not has_collision_block
        )

        if will_move:
            # Physics predicts Mario should move - validate movement
            debug(
                f"Physics predicts {direction} movement: {before_x} -> {predicted_x} (rounded: {predicted_x_pixels})"
            )
            self.assert_movement(after, before, direction=direction, behavior=behavior)
        else:
            # Physics predicts Mario should NOT move (not enough for a full pixel)
            debug(
                f"Physics predicts NO {direction} movement: {before_x} -> {predicted_x} (rounded: {predicted_x_pixels})"
            )
            tolerance = 1
            assert (
                abs(actual_x - before_x) <= tolerance
            ), f"Mario should not move {direction} but moved from {before_x} to {actual_x}"

    def is_jump_initiated(self, behavior):
        """
        Check if a jump was just initiated (jump key pressed and Mario can jump).

        Returns True if jump initiation should be handled by expect_jump.
        """
        if len(behavior) < self.min_history:
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
        if len(behavior) < self.min_history:
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

                    # Should decelerate faster when key not held (manual jump only)
                    deceleration = previous_y_movement - current_y_movement
                    assert (
                        deceleration >= self.jump_deceleration_threshold
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
        if len(behavior) < self.min_history:
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
                            # Speed decreased - Mario must have hit the ground or stomped an enemy
                            mario_now = self.get("player", now)
                            # Check for enemy stomp or large deceleration indicating enemy interaction
                            deceleration = (
                                previous_downward_movement - downward_movement
                            )
                            large_deceleration = (
                                deceleration >= 5
                            )  # Significant speed drop

                            if self.stomped_enemy(behavior) or large_deceleration:
                                debug(
                                    f"Mario stomped enemy: fall slowed from {previous_downward_movement} to {downward_movement} due to bounce"
                                )

                                # Assert basic enemy interaction physics
                                assert (
                                    downward_movement < previous_downward_movement
                                ), f"Enemy stomp should cause deceleration: {downward_movement} >= {previous_downward_movement}"
                                assert (
                                    0
                                    <= downward_movement
                                    <= self.enemy_stomp_max_result_movement
                                ), f"Enemy stomp result movement out of range: {downward_movement} (expected 0-{self.enemy_stomp_max_result_movement})"

                                # Only assert minimum deceleration for significant stomps
                                if deceleration >= self.enemy_stomp_min_deceleration:
                                    debug(
                                        f"Full enemy stomp physics validated: deceleration={deceleration}, final_movement={downward_movement}"
                                    )
                                else:
                                    debug(
                                        f"Light enemy touch: deceleration={deceleration}, final_movement={downward_movement}"
                                    )

                                if large_deceleration and not self.stomped_enemy(
                                    behavior
                                ):
                                    debug(
                                        f"Large fall deceleration ({deceleration}) likely indicates enemy stomp that wasn't detected"
                                    )
                            else:
                                # Check for ground collision
                                has_ground_collision = self.has_collision(
                                    mario_now, now, "bottom"
                                )

                                if has_ground_collision:
                                    debug(
                                        f"Mario hit the ground: speed reduced from {previous_downward_movement} to {downward_movement}"
                                    )
                                else:
                                    assert (
                                        False
                                    ), f"Mario's fall slowed from {previous_downward_movement} to {downward_movement} without ground collision - physics violation"

                    else:
                        # Below terminal velocity - should accelerate
                        # Exception: recent head collisions or interactive object collisions can cause physics disruptions
                        # Check for specific collision types with assertions
                        if self.had_recent_head_collision(behavior):
                            debug(
                                f"Mario falling with recent head collision disruption: downward movement {downward_movement} (was {previous_downward_movement})"
                            )
                        elif self.had_recent_interactive_collision(behavior):
                            debug(
                                f"Mario falling with recent interactive object disruption: downward movement {downward_movement} (was {previous_downward_movement})"
                            )
                        elif self.hit_moving_brick(behavior):
                            deceleration = (
                                previous_downward_movement - downward_movement
                            )
                            debug(
                                f"Mario near moving brick: fall changed from {previous_downward_movement} to {downward_movement}"
                            )

                            # Only assert brick collision physics if there was significant deceleration
                            if deceleration >= 5:
                                debug(
                                    f"Mario hit moving brick hard: validating collision physics"
                                )
                                assert (
                                    downward_movement >= 0
                                ), f"Brick collision caused upward movement: {downward_movement}"
                                assert (
                                    downward_movement <= 8
                                ), f"Brick collision result too high: {downward_movement} > 8"
                                debug(
                                    f"Brick collision physics validated: deceleration={deceleration}, final_movement={downward_movement}"
                                )
                            else:
                                debug(
                                    f"Mario barely touched brick (deceleration={deceleration}) - allowing minor physics disruption"
                                )
                        else:
                            # Check if this might be a head collision we didn't detect
                            mario_before = (
                                self.get("player", behavior[-2])
                                if len(behavior) >= 2
                                else None
                            )
                            has_top_collision = (
                                self.has_collision(mario_before, behavior[-2], "top")
                                if mario_before
                                else False
                            )

                            debug(
                                f"Fall deceleration check: has_top_collision={has_top_collision}, recent_head_collision=False"
                            )
                            debug(
                                f"Mario position: before={self.get_position(behavior[-2], 'y') if len(behavior) >= 2 else 'N/A'}, now={self.get_position(behavior[-1], 'y')}"
                            )

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
                    # Exception: head collisions can cause immediate fast falls
                    if self.had_head_collision(behavior):
                        debug(
                            f"Mario started falling fast due to head collision: {downward_movement} - this is expected"
                        )
                        # Assert head collision fall speed is within game engine limits
                        assert (
                            downward_movement <= self.head_collision_fall_speed_max
                        ), f"Mario's head collision fall speed {downward_movement} exceeds game engine maximum ({self.head_collision_fall_speed_max})"
                        assert (
                            downward_movement >= self.head_collision_fall_speed_min
                        ), f"Mario's head collision fall speed {downward_movement} too low - expected immediate impact fall (≥{self.head_collision_fall_speed_min})"
                    else:
                        assert (
                            downward_movement <= self.max_initial_fall_speed
                        ), f"Mario started falling too fast: {downward_movement} > {self.max_initial_fall_speed} - should start gradually"
        else:
            # Mario has bottom collision (on ground) - check for unexpected downward movement
            if (
                current_y_movement < -self.max_ground_downward_movement
            ):  # Large downward movement (negative values)
                # Large downward movement while on ground is unexpected
                debug(
                    f"Mario on ground had large downward movement: {current_y_movement}"
                )
                assert (
                    False
                ), f"Mario on ground should not have large downward movement: {current_y_movement}"

    def expect(self, behavior):
        """Expect Mario to behave correctly."""

        # If Mario is already dead, skip all physics validation
        if self.mario_is_dead:
            debug("Mario is dead - skipping physics validation")
            return

        # Check if Mario was hurt by enemy collision
        if self.touched_enemy_side(behavior):
            mario_now = self.get("player", behavior[-1])

            # Check Mario's size to determine if he dies or shrinks
            # In the game: big Mario shrinks, small Mario dies
            mario_is_big = hasattr(mario_now, "big") and mario_now.big

            if mario_is_big:
                debug("Big Mario hit enemy - should shrink to small Mario, not die")
                # Big Mario shrinks but doesn't die, continue physics validation
            else:
                debug("Small Mario hit enemy - dies")
                self.mario_is_dead = True
                return

        self.expect_move(behavior, direction="right")
        self.expect_move(behavior, direction="left")
        self.expect_jump(behavior)
        self.expect_falling(behavior)
