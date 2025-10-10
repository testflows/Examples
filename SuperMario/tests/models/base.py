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

        # Check each box for a collision using the simple collides method
        for box in boxes:
            if box is element:
                continue

            if self.game.vision.collides(element.box, box.box):
                self.game.vision.overlay(boxes=[element.box, box.box])
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

    def has_right_touch(self, element, state, objects=None):
        """Check if element has collision on the right side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly to the right of the element
        test_box1 = element.box.copy()
        test_box2 = element.box.copy()
        test_box1.x += 1  # Move 1 pixel to the right
        test_box1.y += 1  # Move 1 pixel down
        test_box2.x += 1  # Move 1 pixel to the right
        test_box2.y -= 1  # Move 1 pixel up

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision using direct colliderect (same as game)
        for box in boxes:
            if box is element:
                continue
            if test_box1.colliderect(box.box) or test_box2.colliderect(box.box):
                return True
        return False

    def has_left_touch(self, element, state, objects=None):
        """Check if element has collision on the left side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly to the left of the element
        test_box1 = element.box.copy()
        test_box2 = element.box.copy()
        test_box1.x -= 1  # Move 1 pixel to the left
        test_box1.y += 1  # Move 1 pixel down
        test_box2.x -= 1  # Move 1 pixel to the left
        test_box2.y -= 1  # Move 1 pixel up

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision using direct colliderect (same as game)
        for box in boxes:
            if box is element:
                continue
            if test_box1.colliderect(box.box) or test_box2.colliderect(box.box):
                return True
        return False

    def has_bottom_touch(self, element, state, objects=None):
        """Check if element has collision on the bottom side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly below the element - EXACTLY like game's check_is_falling
        test_box = element.box.copy()
        test_box.y += 1  # Use same tolerance as game (1 pixel, not 2)

        # Gather all boxes from state.boxes based on the provided keys
        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Use EXACTLY the same collision detection as game's check_is_falling
        # This ensures identical edge detection behavior at pipe boundaries
        for box in boxes:
            if box is element:
                continue
            # Use pygame's colliderect directly (same as game.vision.collides)
            if test_box.colliderect(box.box):
                return True
        return False

    def has_top_touch(self, element, state, objects=None):
        """Check if element has collision on the top side."""
        if objects is None:
            objects = self.solid_objects

        # Create a test box slightly above the element
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
            if test_box.colliderect(box.box):
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
