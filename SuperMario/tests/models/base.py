"""Base model class."""

from testflows.core import debug


class Model:
    """Base model class."""

    def __init__(self, game):
        self.game = game
        self.solid_objects = [
            "box",
            "brick",
            "pipe",
            "ground",
            "step",
            "slider",
            "collider",
        ]

        self.stompable_enemy_objects = [
            "enemy",
            "goomba",
            "koopa",
            "flykoopa",
        ]

    def get(self, name, state):
        """Find element in the specified state."""
        elements = state.boxes.get(name, [])
        element = elements[0] if elements else None
        return element

    def is_key_pressed(self, state, key):
        """Return True if the given key is pressed in the state."""
        return state.keys.key_code(key) in state.keys

    def get_pressed_keys(self, state):
        """Extract pressed keys from behavior state."""
        return {
            "right": self.is_key_pressed(state, "right"),
            "left": self.is_key_pressed(state, "left"),
            "jump": self.is_key_pressed(state, "a"),
            "action": self.is_key_pressed(state, "s"),
            "down": self.is_key_pressed(state, "down"),
        }

    def has_collision(self, element, state, objects=None):
        """
        Check if the element has a collision with another object.

        Args:
            element: The element to check collisions for.
            state: The game state, which contains state.boxes (a dictionary mapping keys to lists of box objects).
            objects (iterable, optional): Specific keys from state.boxes to check. If None, all objects are used.

        Returns:
            bool: True if the element collides with any object, False otherwise.
        """
        if objects is None:
            objects = self.solid_objects

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision using pygame's colliderect (same as game)
        for box in boxes:
            if box is element:
                continue

            if element.box.colliderect(box.box):
                return True

        return False

    def get_position(self, state, axis="x"):
        """Return Mario's coordinate from the given state."""
        mario = self.get("player", state)
        if mario is None:
            return None
        if axis == "x":
            return mario.box.x
        return mario.box.y

    def get_positions(self, *states, axis="x"):
        """Return Mario's positions from multiple states."""
        return tuple(self.get_position(state, axis) for state in states)

    def is_at_left_boundary(self, element, state):
        """Check if element is at the left boundary."""
        return element.box.x == state.start_x

    def is_at_right_boundary(self, element, state):
        """Check if element is at the right boundary."""
        return element.box.x == state.end_x - element.box.w

    def is_past_left_boundary(self, element, state):
        """Check if element is past the left boundary (indicates a bug)."""
        return element.box.x < state.start_x

    def is_past_right_boundary(self, element, state):
        """Check if element is past the right boundary (indicates a bug)."""
        return element.box.x > state.end_x - element.box.w

    def has_right_touch(self, element, element_before, state, objects=None):
        """Check if element has collision on the right side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly to the right of the element
        test_box1 = element.box.copy()
        test_box2 = element.box.copy()
        test_box1.x += 1  # Move 1 pixel to the right
        test_box1.y = element_before.box.y + 1  # Move 1 pixel down
        test_box2.x += 1  # Move 1 pixel to the right
        test_box2.y = element_before.box.y - 1  # Move 1 pixel up

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision using direct colliderect (same as game)
        # The game uses spritecollideany to detect overlap, then checks position:
        # if player.rect.x < collider.rect.x: right-side collision (player to left of collider)
        for box in boxes:
            if box is element:
                continue
            if test_box1.colliderect(box.box) or test_box2.colliderect(box.box):
                # Verify it's a right-side collision: element is to the left of box
                # (matching game logic: if self.player.rect.x < collider.rect.x)
                if element.box.x < box.box.x:
                    return True
        return False

    def has_left_collision(self, element, state, objects=None):
        """Check if element has actual collision on the left side (overlap detection)."""
        if objects is None:
            objects = self.solid_objects

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            # Check for actual overlap (matching spritecollideany behavior)
            if element.box.colliderect(box.box):
                # Verify it's a left-side collision (box is to the left of element)
                # Element's left edge should be near or past box's right edge
                if element.box.left <= box.box.right:
                    return True
        return False

    def has_right_collision(self, element, state, objects=None):
        """Check if element has actual collision on the right side (overlap detection)."""
        if objects is None:
            objects = self.solid_objects

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            # Check for actual overlap (matching spritecollideany behavior)
            if element.box.colliderect(box.box):
                # Verify it's a right-side collision (box is to the right of element)
                # Element's right edge should be near or past box's left edge
                if element.box.right >= box.box.left:
                    return True
        return False

    def has_left_touch(self, element, element_before, state, objects=None):
        """Check if element has collision on the left side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly to the left of the element
        test_box1 = element.box.copy()
        test_box2 = element.box.copy()
        test_box1.x -= 1  # Move 1 pixel to the left
        test_box1.y = element_before.box.y + 1  # Move 1 pixel down
        test_box2.x -= 1  # Move 1 pixel to the left
        test_box2.y = element_before.box.y - 1  # Move 1 pixel up

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision using direct colliderect (same as game)
        # The game uses spritecollideany to detect overlap, then checks position:
        # else: left-side collision (player to right of collider)
        for box in boxes:
            if box is element:
                continue
            if test_box1.colliderect(box.box) or test_box2.colliderect(box.box):
                # Verify it's a left-side collision: element is to the right of box
                # (matching game logic: else case when player.rect.x >= collider.rect.x)
                if element.box.x >= box.box.x:
                    return True
        return False

    def has_bottom_collision(self, element, state, objects=None):
        """Check if element has collision on the bottom side at current position."""
        if objects is None:
            objects = self.solid_objects

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            if (
                element.box.colliderect(box.box)
                and element.box.top <= box.box.top
                and abs(element.box.bottom - box.box.top) <= 1
            ):
                return True
        return False

    def has_bottom_touch(self, element, state, objects=None):
        """Check if element has touch on the bottom side."""
        if objects is None:
            objects = self.solid_objects

        test_box = element.box.copy()
        test_box.y += 1

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            if test_box.colliderect(box.box):
                if (
                    element.box.top <= box.box.top
                    and abs(element.box.bottom - box.box.top) <= 1
                ):
                    return True
        return False

    def has_collision_causing_horizontal_adjustment(
        self,
        element_now,
        element_before,
        element_right_before,
        state_now,
        state_before,
        state_right_before,
        side=None,
    ):
        """
        Check if element has a horizontal collision that causes a position adjustment.

        This is intended to mirror cases where the game snaps Mario horizontally, such as:
        - Side collisions with solid level geometry (walls, pipes, boxes, bricks)
        - Kicking a non-sliding shell/koopa from the side
        - Wall pinning (multi-frame contact)
        - Head collisions causing horizontal shoves
        """
        # New side collision with solid objects (box, brick, pipe, ground, step, collider)
        check_left = side in (None, "left")
        check_right = side in (None, "right")

        left_touch_now = (
            self.has_left_touch(
                element_now, element_before, state_now, objects=self.solid_objects
            )
            if check_left
            else False
        )
        right_touch_now = (
            self.has_right_touch(
                element_now, element_before, state_now, objects=self.solid_objects
            )
            if check_right
            else False
        )
        left_touch_before = (
            self.has_left_touch(
                element_before,
                element_right_before,
                state_before,
                objects=self.solid_objects,
            )
            if check_left
            else False
        )
        right_touch_before = (
            self.has_right_touch(
                element_before,
                element_right_before,
                state_before,
                objects=self.solid_objects,
            )
            if check_right
            else False
        )
        has_new_solid_side_collision = (left_touch_now and not left_touch_before) or (
            right_touch_now and not right_touch_before
        )

        # Sometimes Mario gets pinned against a wall for multiple frames:
        # touch started in the previous frame and is still present now while he can't move.
        # Treat that as a collision-caused adjustment so "stayed in place" checks are skipped.
        left_touch_right_before = (
            self.has_left_touch(
                element_right_before,
                element_before,
                state_right_before,
                objects=self.solid_objects,
            )
            if check_left
            else False
        )
        right_touch_right_before = (
            self.has_right_touch(
                element_right_before,
                element_before,
                state_right_before,
                objects=self.solid_objects,
            )
            if check_right
            else False
        )
        pinned_left = (
            left_touch_now and left_touch_before and not left_touch_right_before
        )
        pinned_right = (
            right_touch_now and right_touch_before and not right_touch_right_before
        )

        # New head collision causing horizontal adjustment (e.g., Mario hits a brick from below and is shoved sideways)
        top_touch_before = self.has_top_touch(
            element_before, state_before, objects=self.solid_objects
        )
        top_touch_right_before = self.has_top_touch(
            element_right_before, state_right_before, objects=self.solid_objects
        )
        head_collision_before = top_touch_before and not top_touch_right_before

        # New side collision with shell/koopa (kicking shell)
        # Use actual collision detection (overlap) rather than just touch for shell kicks
        shell_objects = ["koopa", "shell"]
        left_shell_collision_now = (
            self.has_left_collision(element_now, state_now, objects=shell_objects)
            if check_left
            else False
        )
        right_shell_collision_now = (
            self.has_right_collision(element_now, state_now, objects=shell_objects)
            if check_right
            else False
        )
        left_shell_collision_before = (
            self.has_left_collision(element_before, state_before, objects=shell_objects)
            if check_left
            else False
        )
        right_shell_collision_before = (
            self.has_right_collision(
                element_before, state_before, objects=shell_objects
            )
            if check_right
            else False
        )
        has_new_shell_collision = (
            left_shell_collision_now and not left_shell_collision_before
        ) or (right_shell_collision_now and not right_shell_collision_before)

        # Also check for shell touches (for cases where touch detection is needed)
        left_shell_touch_now = (
            self.has_left_touch(
                element_now, element_before, state_now, objects=shell_objects
            )
            if check_left
            else False
        )
        right_shell_touch_now = (
            self.has_right_touch(
                element_now, element_before, state_now, objects=shell_objects
            )
            if check_right
            else False
        )
        left_shell_touch_before = (
            self.has_left_touch(
                element_before,
                element_right_before,
                state_before,
                objects=shell_objects,
            )
            if check_left
            else False
        )
        right_shell_touch_before = (
            self.has_right_touch(
                element_before,
                element_right_before,
                state_before,
                objects=shell_objects,
            )
            if check_right
            else False
        )
        has_new_shell_side_collision = (
            left_shell_touch_now and not left_shell_touch_before
        ) or (right_shell_touch_now and not right_shell_touch_before)

        return (
            has_new_solid_side_collision
            or has_new_shell_side_collision
            or has_new_shell_collision
            or pinned_left
            or pinned_right
            or head_collision_before
        )

    def has_collision_causing_vertical_adjustment(
        self,
        element_now,
        element_before,
        element_right_before,
        state_now,
        state_before,
        state_right_before,
    ):
        """
        Check if element has a vertical collision that causes a position adjustment.

        This is intended to mirror cases where the game snaps Mario vertically, such as:
        - Landing on solid ground/steps/blocks (bottom snap)
        - Hitting a solid from below (top snap)
        - Stomping an enemy (bottom snap onto enemy, then bounce)
        """
        # New bottom collision with solid objects (landing)
        bottom_touch_now = self.has_bottom_touch(
            element_now, state_now, objects=self.solid_objects
        )
        bottom_touch_before = self.has_bottom_touch(
            element_before, state_before, objects=self.solid_objects
        )
        has_new_bottom_collision = bottom_touch_now and not bottom_touch_before

        # New top collision with solid objects (head hit)
        # Handle multi-frame top touches (e.g., brick bumps that span multiple frames)
        top_touch_now = self.has_top_touch(
            element_now, state_now, objects=self.solid_objects
        )
        top_touch_before = self.has_top_touch(
            element_before, state_before, objects=self.solid_objects
        )
        top_touch_right_before = self.has_top_touch(
            element_right_before, state_right_before, objects=self.solid_objects
        )
        # Detect new top collision: either a new touch, or a touch that persists
        # from right_before -> before -> now (multi-frame contact with bumping brick)
        has_new_top_collision = (top_touch_now and not top_touch_before) or (
            top_touch_now and top_touch_before and not top_touch_right_before
        )

        # New stomp on enemy (bottom snap onto enemy)
        bottom_enemy_touch_now = self.has_bottom_touch(
            element_now, state_now, objects=self.stompable_enemy_objects
        )
        bottom_enemy_touch_before = self.has_bottom_touch(
            element_before, state_before, objects=self.stompable_enemy_objects
        )
        has_new_enemy_stomp = bottom_enemy_touch_now and not bottom_enemy_touch_before

        return has_new_bottom_collision or has_new_top_collision or has_new_enemy_stomp

    def has_collision_causing_position_adjustment(
        self,
        element_now,
        element_before,
        element_right_before,
        state_now,
        state_before,
        state_right_before,
    ):
        """
        Backwards-compatible wrapper that checks for any collision-causing position
        adjustment (horizontal or vertical).
        """
        return self.has_collision_causing_horizontal_adjustment(
            element_now,
            element_before,
            element_right_before,
            state_now,
            state_before,
            state_right_before,
        ) or self.has_collision_causing_vertical_adjustment(
            element_now,
            element_before,
            element_right_before,
            state_now,
            state_before,
            state_right_before,
        )

    def has_top_collision(self, element, state, objects=None):
        """Check if element has actual collision on the top side (overlap detection)."""
        if objects is None:
            objects = self.solid_objects

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            # Check for actual overlap (matching spritecollideany behavior)
            if element.box.colliderect(box.box):
                # Verify it's a top collision (element is below box)
                if element.box.top > box.box.top:
                    return True
        return False

    def has_top_touch(self, element, state, objects=None):
        """Check if element has collision on the top side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly above the element
        # This matches the approach used by has_bottom_touch and has_left_touch/has_right_touch
        # The game uses spritecollideany which checks for overlap, then checks direction
        # By moving up 1 pixel and checking for collision, we detect if there's something above
        test_box = element.box.copy()
        test_box.y -= 1  # Move 1 pixel up

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision using direct colliderect (same as game)
        for box in boxes:
            if box is element:
                continue
            # Check if test box (Mario moved up 1 pixel) collides with the box
            # This detects if there's something above Mario that he could hit
            if test_box.colliderect(box.box):
                # Also verify this is a top collision (Mario's top is below sprite's top)
                # This matches the game's check: if self.player.rect.top > sprite.rect.top
                if element.box.top > box.box.top:
                    return True
        return False

    def direction(self, state, in_the_air):
        """Return the direction Mario based on the keys pressed."""

        keys = self.get_pressed_keys(state)
        right_pressed = keys.get("right", False)
        left_pressed = keys.get("left", False)

        if in_the_air:
            # Air physics: right has precedence (jumping/falling state)
            if right_pressed:
                direction = "right"
            elif left_pressed:
                direction = "left"
            else:
                return  # No keys pressed
        else:
            # Ground physics: left has precedence (walking state)
            if left_pressed:
                direction = "left"
            elif right_pressed:
                direction = "right"
            else:
                return  # No keys pressed

        return direction

    def assert_with_success(self, condition, msg):
        """Assert a condition and print success message if it passes."""
        if condition:
            debug(f"✓ Mario {msg}")
        else:
            assert False, f"Mario failed to: {msg}"
