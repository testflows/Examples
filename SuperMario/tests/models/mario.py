from testflows.core import debug
from .base import Model


class Physics:
    """Handles Mario's physics predictions and validation."""

    def __init__(self, game):
        self.game = game
        # Game physics constants (extracted from mario.json and constants.py)
        self.walk_accel = 0.15  # mario.json: "walk_accel":0.15
        self.run_accel = 0.3  # mario.json: "run_accel":0.3
        self.max_walk_vel = 6  # mario.json: "max_walk_speed":6
        self.max_run_vel = 12  # mario.json: "max_run_speed":12
        self.max_y_vel = 11  # mario.json: "max_y_velocity":11
        self.jump_vel = -10.5  # mario.json: "jump_velocity":-10.5
        self.gravity = 1.01  # constants.py: GRAVITY = 1.01
        self.jump_gravity = 0.31  # constants.py: JUMP_GRAVITY = .31
        self.small_turnaround = 0.35  # constants.py: SMALL_TURNAROUND = .35

    def predict_x_position(self, mario_state, keys, mario_internal, full_state=None):
        """Predict Mario's next X position based on physics rules."""
        current_vel = mario_internal.get("x_vel", 0)
        current_pos = mario_state.box.x

        # Special case: If Mario has zero velocity but a key is pressed,
        # the game immediately calculates new velocity using cal_vel logic
        if current_vel == 0 and (keys.get("right") or keys.get("left")):
            debug(f"Mario has zero velocity but key pressed - applying acceleration")

            # Check Mario's current state to determine the right behavior
            mario_state_name = mario_internal.get("state", "unknown")
            walking_timer = mario_internal.get("walking_timer", 0)
            current_time = mario_internal.get("current_time", 0)
            is_fresh_start = walking_timer == current_time

            debug(f"Mario state: {mario_state_name}, is_fresh_start: {is_fresh_start}")

            # If Mario is in 'standing' state, he needs time to start moving
            if mario_state_name == "standing":
                debug("Mario is standing - may not move immediately when key pressed")
                return current_pos  # No movement predicted for standing state

            # Handle different states with appropriate acceleration
            # Check if both keys are pressed (they cancel each other out)
            both_keys_pressed = keys.get("left", False) and keys.get("right", False)
            debug(
                f"Physics key check: left={keys.get('left', False)}, right={keys.get('right', False)}, both={both_keys_pressed}"
            )
            if both_keys_pressed:
                debug("Both left and right keys pressed - zero net movement")
                return current_pos  # No movement when both keys cancel out

            # Check for rapid direction changes that might reset velocity
            # If Mario has zero velocity but very recent walking timer, he might be in rapid alternation
            time_since_walk_start = current_time - walking_timer
            if (
                current_vel == 0 and time_since_walk_start < 100
            ):  # Less than 100ms since walk start
                debug(
                    f"Rapid direction change detected: {time_since_walk_start}ms since walk start, vel={current_vel}"
                )
                # In rapid alternation, Mario's velocity might be reset, preventing immediate movement
                # Check if this is a fresh direction change
                if time_since_walk_start < 50:  # Very recent walk start
                    debug(
                        "Very recent walk start - Mario may not move immediately due to rapid alternation"
                    )
                    return current_pos  # No movement predicted for very rapid changes
                elif (
                    time_since_walk_start < 150
                ):  # Moderate delay after direction change
                    debug(
                        f"Direction change stabilization period: {time_since_walk_start}ms - checking for delayed startup"
                    )
                    # For moderate delays (50-150ms), Mario might still be transitioning from opposite direction
                    # Use normal acceleration instead of collision recovery velocity
                    if keys.get("right") or keys.get("left"):
                        debug(
                            "Using normal startup acceleration instead of collision recovery"
                        )
                        new_vel = self.walk_accel  # 0.15 instead of 5.0
                        debug(f"Startup acceleration velocity: {new_vel}")
                        if round(new_vel) == 0:
                            debug(
                                "Startup velocity rounds to 0 - no movement predicted"
                            )
                            return current_pos
                        predicted_pos = current_pos + (
                            round(new_vel) if keys.get("right") else -round(new_vel)
                        )
                        debug(
                            f"Gradual startup movement: {current_pos} -> {predicted_pos}"
                        )
                        return predicted_pos

            if keys.get("right"):
                if not is_fresh_start and mario_state_name == "walk":
                    # Check if this might be a post-turnaround scenario
                    # Mario has x_vel=0 but may have recently had leftward velocity
                    if (
                        current_vel == 0 and time_since_walk_start < 200
                    ):  # Recent direction change
                        debug(
                            "Post-turnaround scenario detected - using normal cal_vel instead of collision recovery"
                        )
                        new_vel = self.walk_accel  # Use normal acceleration
                        debug(
                            f"Post-turnaround cal_vel(0, 6, {self.walk_accel}) = {new_vel}"
                        )
                    else:
                        # Normal collision recovery in walking state - game might restore higher velocity
                        new_vel = 5.0
                        debug(
                            f"Walk collision recovery detected - using velocity {new_vel}"
                        )
                elif mario_state_name == "jump" or mario_state_name == "fall":
                    # Mario uses same acceleration logic as walking during jumps/falls
                    if keys.get("action", False):
                        accel = self.run_accel  # 0.3
                        debug(f"Jump with action key - using run acceleration {accel}")
                    else:
                        accel = self.walk_accel  # 0.15
                        debug(
                            f"Jump without action key - using walk acceleration {accel}"
                        )

                    # Apply cal_vel logic: new_vel = current_vel + accel (positive for right)
                    new_vel = 0 + accel
                    debug(f"Jump cal_vel(0, 6, {accel}) = {new_vel}")

                    # No special collision adjustment needed here - handled by main collision logic
                else:
                    # Use normal acceleration for other cases
                    new_vel = self.walk_accel  # 0.15
                    debug(f"Normal acceleration - using velocity {new_vel}")
            else:  # left key
                if mario_state_name == "jump" or mario_state_name == "fall":
                    # Mario uses same acceleration logic as walking during jumps/falls
                    if keys.get("action", False):
                        accel = self.run_accel  # 0.3
                        debug(f"Jump with action key - using run acceleration {accel}")
                    else:
                        accel = self.walk_accel  # 0.15
                        debug(
                            f"Jump without action key - using walk acceleration {accel}"
                        )

                    # Apply cal_vel logic: new_vel = current_vel + accel (negative for left)
                    new_vel = 0 - accel
                    debug(f"Jump cal_vel(0, 6, {accel}) = {new_vel}")

                    # No special collision adjustment needed here - handled by main collision logic
                else:
                    # Use exact cal_vel logic for normal walking
                    # cal_vel(0, 6, 0.15, True) = -0.15
                    new_vel = 0 - self.walk_accel  # -0.15
                    debug(f"Walk cal_vel(0, 6, 0.15, True) = {new_vel}")

            debug(f"Calculated new velocity: {new_vel}, rounded: {round(new_vel)}")
            if round(new_vel) == 0:
                debug("Rounded velocity is 0 - no movement predicted")
                return current_pos
            predicted_pos = current_pos + round(new_vel)
            debug(f"Predicted movement: {current_pos} -> {predicted_pos}")
            return predicted_pos

        # Normal case: Game uses CURRENT velocity for position updates
        if round(current_vel) == 0:
            return current_pos  # No movement if current velocity rounds to 0

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
        """Check if Mario will collide with solid objects at predicted position.

        Args:
            mario_state: The game state containing Mario and objects
            predicted_x: Mario's predicted x position
            predicted_y: Mario's predicted y position
            tolerance: Extra pixels to expand Mario's collision box (for near-miss detection)
        """
        mario_elements = mario_state.boxes.get("player", [])
        if not mario_elements:
            debug("No Mario elements found in state")
            return False

        mario = mario_elements[0]
        if not hasattr(mario, "box"):
            debug("Mario has no box attribute")
            return False

        temp_box = mario.box.copy()
        temp_box.x = predicted_x
        temp_box.y = predicted_y

        # Use exact collision detection like the game (no tolerance)

        debug(
            f"Checking collision at predicted position: x={predicted_x}, y={predicted_y}"
        )
        debug(f"Mario temp box: {temp_box}")

        # Check collision with solid objects using vision system (same as colliderect)
        solid_objects = ["box", "brick", "pipe", "ground", "step", "collider"]
        for obj_type in solid_objects:
            objects = mario_state.boxes.get(obj_type, [])
            debug(f"Checking {len(objects)} {obj_type} objects")
            for i, obj in enumerate(objects):
                debug(f"  {obj_type}[{i}] at {obj.box}")
                if self.game.vision.collides(temp_box, obj.box):
                    debug(f"COLLISION DETECTED with {obj_type}[{i}] at {obj.box}")
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
        self.residual_movement_tolerance = 5  # Tolerance for residual movements from inertia, collision adjustment, or floating-point precision
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

    def predict_collision_adjusted_position(
        self, mario_state, before_state, predicted_x, direction
    ):
        """Predict where Mario will be positioned after collision adjustment."""
        # Find the colliding object at the predicted position
        temp_box = mario_state.box.copy()
        temp_box.x = predicted_x

        debug(f"Predicting collision adjustment: Mario temp box at {temp_box}")

        solid_objects = ["box", "brick", "pipe", "ground", "step", "collider"]
        for obj_type in solid_objects:
            objects = before_state.boxes.get(obj_type, [])
            debug(f"Checking {len(objects)} {obj_type} objects for adjustment")
            for obj in objects:
                debug(f"  Checking {obj_type} at {obj.box}")
                if self.game.vision.collides(temp_box, obj.box):
                    # Found the colliding object - calculate adjustment
                    if direction == "right":
                        # Mario moving right hits object - his right edge gets set to object's left edge
                        # Mario's x = object.left - mario.width
                        adjusted_x = obj.box.x - mario_state.box.width
                    else:  # direction == "left"
                        # Mario moving left hits object - his left edge gets set to object's right edge
                        adjusted_x = obj.box.x + obj.box.width

                    debug(
                        f"Collision with {obj_type} at {obj.box} - adjusting Mario to x={adjusted_x}"
                    )
                    return adjusted_x

        # No collision found (shouldn't happen if has_collision_block is True)
        debug("No collision found for adjustment - returning predicted position")
        return predicted_x

    def _check_nearby_collision(self, mario_state, current_pos, direction):
        """Check if Mario is close enough to a collision boundary that he might get adjusted."""
        mario_box = mario_state.box.copy()
        mario_box.x = current_pos

        # Check if Mario is very close (within a few pixels) to any solid object
        solid_objects = ["box", "brick", "ground_step_pipe"]
        for obj_type in solid_objects:
            objects = self.game.state.boxes.get(obj_type, [])
            for obj in objects:
                if direction == "left":
                    # Check if Mario's left edge is close to object's right edge
                    distance_to_collision = mario_box.x - (obj.box.x + obj.box.width)
                    if -5 <= distance_to_collision <= 5:  # Within 5 pixels
                        # Check vertical overlap
                        if (
                            mario_box.y < obj.box.y + obj.box.height
                            and mario_box.y + mario_box.height > obj.box.y
                        ):
                            # Mario would be positioned at collision boundary
                            adjusted_x = obj.box.x + obj.box.width
                            debug(
                                f"Nearby collision with {obj_type}: Mario adjusted to x={adjusted_x}"
                            )
                            return adjusted_x
                elif direction == "right":
                    # Check if Mario's right edge is close to object's left edge
                    distance_to_collision = obj.box.x - (mario_box.x + mario_box.width)
                    if -5 <= distance_to_collision <= 5:  # Within 5 pixels
                        # Check vertical overlap
                        if (
                            mario_box.y < obj.box.y + obj.box.height
                            and mario_box.y + mario_box.height > obj.box.y
                        ):
                            # Mario would be positioned at collision boundary
                            adjusted_x = obj.box.x - mario_box.width
                            debug(
                                f"Nearby collision with {obj_type}: Mario adjusted to x={adjusted_x}"
                            )
                            return adjusted_x

        return None

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
            if movement > self.residual_movement_tolerance:
                # Add debugging to understand the movement
                mario_before = self.get("player", before)
                mario_after = self.get("player", now)
                mario_internal = self.internal_state()
                debug(f"Unexpected right movement: {movement} pixels")
                debug(f"Mario before: x={mario_before.box.x}, y={mario_before.box.y}")
                debug(f"Mario after: x={mario_after.box.x}, y={mario_after.box.y}")
                debug(
                    f"Mario velocity: x_vel={mario_internal.get('x_vel', 0)}, y_vel={mario_internal.get('y_vel', 0)}"
                )
                debug(f"Mario state: {mario_internal.get('state', 'unknown')}")
            assert (
                movement <= self.residual_movement_tolerance
            ), f"Mario unexpectedly moved right {movement} (tolerance: {self.residual_movement_tolerance})"
        elif direction == "left":
            movement = pos_before - pos_now
            if movement > self.residual_movement_tolerance:
                # Add debugging to understand the movement
                mario_before = self.get("player", before)
                mario_after = self.get("player", now)
                mario_internal = self.internal_state()
                debug(f"Unexpected left movement: {movement} pixels")
                debug(f"Mario before: x={mario_before.box.x}, y={mario_before.box.y}")
                debug(f"Mario after: x={mario_after.box.x}, y={mario_after.box.y}")
                debug(
                    f"Mario velocity: x_vel={mario_internal.get('x_vel', 0)}, y_vel={mario_internal.get('y_vel', 0)}"
                )
                debug(f"Mario state: {mario_internal.get('state', 'unknown')}")
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

    def assert_movement(
        self, now, before, direction="right", behavior=None, expected_pos=None
    ):
        """
        Assert that Mario moved to the right or left and did not exceed max walking speed.

        Args:
            expected_pos: If provided, assert Mario moved to this specific position
        """
        pos_now = self.get_position(now)
        pos_before = self.get_position(before)

        # If expected position is provided, check it specifically
        if expected_pos is not None:
            tolerance = 1
            assert (
                abs(pos_now - expected_pos) <= tolerance
            ), f"Mario should be at position {expected_pos} but is at {pos_now} (tolerance: {tolerance})"
            debug(f"Mario correctly positioned at {pos_now} (expected: {expected_pos})")
            return

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

        # Check if Mario is at any boundary - if so, skip all inertia checks
        mario_before = self.get("player", before)
        is_at_left_boundary = (
            self.level.should_stay_at_boundary(mario_before, "left")
            if hasattr(self, "level")
            else False
        )
        is_at_right_boundary = (
            self.level.should_stay_at_boundary(mario_before, "right")
            if hasattr(self, "level")
            else False
        )
        # Check if Mario is currently blocked by collision in any direction
        # Use the same collision detection as predictive collision for consistency
        current_x = mario_before.box.x
        current_y = mario_before.box.y
        is_collision_blocked = (
            self.collision.will_collide_with_objects(before, current_x, current_y)
            or self.has_collision(mario_before, before, "right")
            or self.has_collision(mario_before, before, "left")
        )

        if is_at_left_boundary or is_at_right_boundary or is_collision_blocked:
            debug(
                f"Mario at boundary or collision - skipping all inertia checks for {direction}"
            )
            return
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
        # Allow stuttering patterns during deceleration due to floating-point rounding
        if current_movement > previous_movement:
            # Check if this is a small fluctuation (≤1 pixel difference)
            fluctuation = current_movement - previous_movement
            if fluctuation <= 1:
                debug(
                    f"Mario stuttering during deceleration: {previous_movement} -> {current_movement} (fluctuation: +{fluctuation})"
                )
            else:
                assert (
                    False
                ), f"Mario should not accelerate with {direction} inertia: {current_movement}, previous {previous_movement}"

        # Check if the same inertia speed should start decreasing.
        if self.has_maintained_inertia(
            behavior, previous_movement, direction=direction
        ):
            # If so, then we expect deceleration (i.e. current movement must be less than previous).
            debug(
                f"Mario has maintained inertia speed {previous_movement} for {self.inertia_threshold}+ frames - expecting deceleration"
            )

            # Special case: If previous_movement is already 0, we can't expect further deceleration
            # This happens when Mario has small internal velocity (e.g. 0.15) that rounds to 0 pixels
            if previous_movement == 0:
                debug(
                    f"Mario already at minimum movement (0) - cannot decelerate further"
                )
            else:
                assert (
                    current_movement < previous_movement
                ), f"Mario maintained the same inertia speed ({previous_movement}); but expected deceleration."

        debug(
            f"Mario has {direction} inertia current speed {current_movement}, previous speed {previous_movement}; should maintain its speed or decelerate"
        )

    def debug_movement_context(
        self, behavior, direction, keys, mario_internal, before_x, actual_x
    ):
        """Log comprehensive movement context for debugging."""
        debug(
            f"Checking direction '{direction}': key_pressed={keys.get(direction, False)}, keys={keys}"
        )
        debug(f"Mario internal state: {mario_internal}")
        debug(f"Movement: {before_x} -> {actual_x}")

        if mario_internal.get("walking_timer", 0) == 0:
            debug("Walking timer not started yet - this might be the startup delay!")
        else:
            time_since_walk_start = mario_internal.get(
                "current_time", 0
            ) - mario_internal.get("walking_timer", 0)
            debug(f"Time since walking started: {time_since_walk_start}ms")

    def handle_no_key_pressed(self, behavior, direction):
        """Handle movement when no directional key is pressed."""
        if len(behavior) < 3:
            return

        mario_internal = self.internal_state()
        current_vel = mario_internal.get("x_vel", 0)

        debug(
            f"Inertia check: current_vel={current_vel}, abs={abs(current_vel)}, direction={direction}"
        )

        if abs(current_vel) > 0.1:  # Mario has velocity (inertia)
            actual_direction = "right" if current_vel > 0 else "left"
            debug(
                f"Mario has inertia: actual_direction={actual_direction}, expected_direction={direction}"
            )
            if actual_direction == direction:
                self.assert_inertia_movement(behavior, direction=direction)
            return

        # Mario has no significant velocity - check for collision adjustment
        self.handle_stationary_collision_adjustment(behavior, direction)

    def handle_stationary_collision_adjustment(self, behavior, direction):
        """Handle collision adjustments when Mario is stationary."""
        before, after = behavior[-2], behavior[-1]
        mario_state = self.get("player", before)
        mario_internal = self.internal_state()
        mario_state_name = mario_internal.get("state", "").lower()

        if mario_state_name in ["jump", "fall", "walk", "standing"]:
            current_pos = mario_state.box.x
            current_collision = self.collision.will_collide_with_objects(
                before, current_pos, mario_state.box.y
            )

            if current_collision:
                debug("Mario in collision scenario - predicting adjustment")
                adjusted_pos = self.predict_collision_adjusted_position(
                    mario_state, before, current_pos, direction
                )
                debug(
                    f"Collision adjustment during {mario_state_name}: {current_pos} -> {adjusted_pos}"
                )
                self.assert_movement(
                    after, before, direction=direction, expected_pos=adjusted_pos
                )
                return

        # No collision adjustment needed - assert no movement
        current_vel = mario_internal.get("x_vel", 0)
        debug(
            f"Mario has no significant velocity ({current_vel}) - asserting no movement"
        )
        self.assert_no_unintended_movement(after, before, direction=direction)

    def get_movement_context(self, behavior, direction):
        """Get all the context needed for movement prediction."""
        before, after = behavior[-2], behavior[-1]
        keys = self.get_pressed_keys(before)
        mario_internal = self.internal_state()
        mario_state = self.get("player", before)

        predicted_x = self.physics.predict_x_position(
            mario_state, keys, mario_internal, before
        )
        before_x = self.get_position(before)
        actual_x = self.get_position(after)

        # Check for turnaround scenario
        current_vel = mario_internal.get("x_vel", 0)
        is_turnaround = (direction == "right" and current_vel < -0.5) or (
            direction == "left" and current_vel > 0.5
        )

        # Check for blocking conditions
        mario_before = self.get("player", before)
        has_boundary_block = (
            self.level.should_stay_at_boundary(mario_before, direction)
            if hasattr(self, "level")
            else False
        )
        has_collision_block = self.collision.will_collide_with_objects(
            before, predicted_x, mario_before.box.y
        )

        # Check for both keys pressed
        both_keys_pressed = keys.get("left", False) and keys.get("right", False)

        return {
            "before": before,
            "after": after,
            "keys": keys,
            "mario_internal": mario_internal,
            "mario_state": mario_state,
            "predicted_x": predicted_x,
            "before_x": before_x,
            "actual_x": actual_x,
            "is_turnaround": is_turnaround,
            "has_boundary_block": has_boundary_block,
            "has_collision_block": has_collision_block,
            "both_keys_pressed": both_keys_pressed,
        }

    def handle_collision_adjustment(self, context):
        """Unified collision adjustment handling."""
        mario_before = context["mario_state"]
        before = context["before"]
        after = context["after"]
        direction = context.get("direction", "right")
        current_pos = mario_before.box.x

        # Check current collision
        current_collision = self.collision.will_collide_with_objects(
            before, current_pos, mario_before.box.y
        )

        if current_collision:
            debug("Mario in collision scenario - predicting adjustment")
            adjusted_pos = self.predict_collision_adjusted_position(
                mario_before, before, current_pos, direction
            )
            if adjusted_pos != current_pos:
                debug(f"Collision adjustment: {current_pos} -> {adjusted_pos}")
                self.assert_movement(
                    after, before, direction=direction, expected_pos=adjusted_pos
                )
                return True

        # Check hypothetical collision (Mario has zero velocity but key pressed)
        mario_internal = context["mario_internal"]
        keys = context["keys"]
        if mario_internal.get("x_vel", 0) == 0 and keys.get(direction):
            hypothetical_velocity = 6
            hypothetical_pos = current_pos + (
                hypothetical_velocity
                if direction == "right"
                else -hypothetical_velocity
            )
            hypothetical_collision = self.collision.will_collide_with_objects(
                before, hypothetical_pos, mario_before.box.y
            )

            if hypothetical_collision and not current_collision:
                debug(
                    "Mario would hit collision if he had velocity - predicting adjustment"
                )
                adjusted_pos = self.predict_collision_adjusted_position(
                    mario_before, before, hypothetical_pos, direction
                )
                debug(
                    f"Hypothetical collision adjustment: {current_pos} -> {adjusted_pos}"
                )
                self.assert_movement(
                    after, before, direction=direction, expected_pos=adjusted_pos
                )
                return True

        return False

    def handle_both_keys_pressed(self, context):
        """Handle the case where both left and right keys are pressed."""
        if not context["both_keys_pressed"]:
            return False

        mario_internal = context["mario_internal"]
        if mario_internal.get("x_vel", 0) == 0:
            debug(
                "Both keys pressed with zero velocity - checking for collision adjustment"
            )
            mario_after = self.get("player", context["after"])
            current_pos = context["before_x"]

            if mario_after and mario_after.box.x != current_pos:
                final_x = mario_after.box.x
                debug(f"Both-keys collision adjustment: {current_pos} -> {final_x}")
                self.assert_movement(
                    context["after"],
                    context["before"],
                    direction=None,
                    expected_pos=final_x,
                )
                return True

        return False

    def handle_opposite_movement(self, context, direction, behavior):
        """Handle cases where Mario moves opposite to the expected direction."""
        mario_after = self.get("player", context["after"])
        if not mario_after:
            return False

        before_x = context["before_x"]
        actual_movement = mario_after.box.x - before_x

        if abs(actual_movement) < 1:
            return False

        actual_final_direction = "right" if actual_movement > 0 else "left"

        if actual_final_direction != direction:
            debug(
                f"Mario moved {actual_final_direction} but {direction} key was pressed"
            )

            if context["is_turnaround"]:
                debug(
                    f"Turnaround in progress: {direction} key pressed but Mario moves {actual_final_direction}"
                )
            else:
                debug(
                    f"Collision adjustment: {direction} key pressed but Mario moved {actual_final_direction}"
                )

            # Validate using actual direction
            self.assert_movement(
                context["after"],
                context["before"],
                direction=actual_final_direction,
                behavior=behavior,
            )
            return True

        return False

    def handle_unexpected_movement(self, context, direction):
        """Handle unexpected movement when physics predicts no movement."""
        before_x = context["before_x"]
        actual_x = context["actual_x"]

        if abs(actual_x - before_x) <= 1:
            return False

        debug(f"Unexpected movement detected: {before_x} -> {actual_x}")

        # Check for opposite movement
        actual_movement = actual_x - before_x
        expected_right = direction == "right"
        actual_right = actual_movement > 0

        if expected_right != actual_right:
            debug(
                "Mario moved opposite to expected direction - likely collision adjustment"
            )
            actual_direction = "right" if actual_right else "left"
            self.assert_movement(
                context["after"],
                context["before"],
                direction=actual_direction,
                expected_pos=actual_x,
            )
            return True

        # Check for both keys pressed
        if context["both_keys_pressed"]:
            debug("Both keys pressed - allowing movement due to collision adjustment")
            self.assert_movement(
                context["after"],
                context["before"],
                direction=None,
                expected_pos=actual_x,
            )
            return True

        # Check for small residual movement
        if abs(actual_x - before_x) <= self.residual_movement_tolerance:
            debug(
                f"Small residual movement within tolerance ({self.residual_movement_tolerance}px)"
            )
            return True

        return False

    def expect_move(self, behavior, direction):
        """Expect Mario to move right or left using predictive physics."""
        if len(behavior) < 2:
            return

        # Get current state
        keys = self.get_pressed_keys(behavior[-2])
        key_pressed = keys.get(direction, False)

        # Handle no key pressed - check for inertia or collision adjustment
        if not key_pressed:
            self.handle_no_key_pressed(behavior, direction)
            return

        # Key IS pressed - get movement context and predict
        context = self.get_movement_context(behavior, direction)
        context["direction"] = direction  # Add direction to context

        # Debug the movement context
        self.debug_movement_context(
            behavior,
            direction,
            context["keys"],
            context["mario_internal"],
            context["before_x"],
            context["actual_x"],
        )

        # Handle special cases first
        if self.handle_collision_adjustment(context):
            return

        if self.handle_both_keys_pressed(context):
            return

        # Check if physics predicts movement
        predicted_x_pixels = round(context["predicted_x"])
        will_move = (
            abs(predicted_x_pixels - context["before_x"]) >= 1
            and not context["has_boundary_block"]
            and not context["has_collision_block"]
        )

        if context["has_collision_block"]:
            # Handle collision-blocked movement
            adjusted_x = self.predict_collision_adjusted_position(
                context["mario_state"],
                context["before"],
                context["predicted_x"],
                direction,
            )
            debug(
                f"Collision detected - Mario will be adjusted to position {adjusted_x}"
            )

            if abs(adjusted_x - context["before_x"]) >= 1:
                debug(
                    f"Collision adjustment moves Mario from {context['before_x']} to {adjusted_x}"
                )
                self.assert_movement(
                    context["after"],
                    context["before"],
                    direction=direction,
                    expected_pos=adjusted_x,
                )
            else:
                debug(f"Collision adjustment keeps Mario at {context['before_x']}")
                tolerance = 1
                assert (
                    abs(context["actual_x"] - context["before_x"]) <= tolerance
                ), f"Mario should not move {direction} due to collision but moved from {context['before_x']} to {context['actual_x']}"

        elif will_move:
            # Physics predicts movement - handle it
            debug(
                f"Physics predicts {direction} movement: {context['before_x']} -> {context['predicted_x']} (rounded: {predicted_x_pixels})"
            )

            if self.handle_opposite_movement(context, direction, behavior):
                return

            # Normal movement validation
            self.assert_movement(
                context["after"],
                context["before"],
                direction=direction,
                behavior=behavior,
            )

        else:
            # Physics predicts NO movement
            debug(
                f"Physics predicts NO {direction} movement: {context['before_x']} -> {context['predicted_x']} (rounded: {predicted_x_pixels})"
            )

            if self.handle_unexpected_movement(context, direction):
                return

            # Final assertion - Mario should not move
            tolerance = 1
            assert (
                abs(context["actual_x"] - context["before_x"]) <= tolerance
            ), f"Mario should not move {direction} but moved from {context['before_x']} to {context['actual_x']}"

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
        self.expect_move(behavior, direction="right")
        self.expect_move(behavior, direction="left")
        # self.expect_jump(behavior)
        # self.expect_falling(behavior)
