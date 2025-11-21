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

    def is_at_right_boundary(self, element, state):
        """Check if element is at the right boundary."""
        return element.box.x == state.end_x - element.box.w

    def is_at_left_boundary(self, element, state):
        """Check if element is at the left boundary."""
        return element.box.x == state.start_x

    def is_past_right_boundary(self, element, state):
        """Check if element is past the right boundary (indicates a bug)."""
        return element.box.x > state.end_x - element.box.w

    def is_past_left_boundary(self, element, state):
        """Check if element is past the left boundary (indicates a bug)."""
        return element.box.x < state.start_x

    def is_visible_in_viewport(self, element, state):
        """Return True if the element intersects the current viewport bounds."""
        viewport = getattr(state, "viewport", None)
        if viewport is None or element is None:
            return True

        vx, vy, vw, vh = viewport
        element_rect = element.box
        right = vx + vw
        bottom = vy + vh

        return (
            element_rect.left >= vx
            and element_rect.right <= right
            and element_rect.top >= vy
            and element_rect.bottom <= bottom
        )

    def has_right_touch(self, element, element_before, state, objects=None):
        """Check if element has collision on the right side."""
        if objects is None:
            objects = self.solid_objects

        test_box_now = element.box.copy()
        test_box_now.x += 1
        test_box_before = element.box.copy()
        test_box_before.x += 1
        test_box_before.y = element_before.box.y

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            if test_box_now.colliderect(box.box) or test_box_before.colliderect(
                box.box
            ):
                if element.box.x <= box.box.x:
                    return True
        return False

    def has_left_touch(self, element, element_before, state, objects=None):
        """Check if element has collision on the left side."""
        if objects is None:
            objects = self.solid_objects

        test_box_now = element.box.copy()
        test_box_now.x -= 1
        test_box_before = element.box.copy()
        test_box_before.x -= 1
        test_box_before.y = element_before.box.y

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            if test_box_now.colliderect(box.box) or test_box_before.colliderect(
                box.box
            ):
                if element.box.x >= box.box.x:
                    return True
        return False

    def has_top_touch(self, element, state, objects=None):
        """Check if element has collision on the top side."""
        if objects is None:
            objects = self.solid_objects

        test_box = element.box.copy()
        test_box.y -= 1

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        for box in boxes:
            if box is element:
                continue
            if test_box.colliderect(box.box):
                if element.box.top > box.box.top:
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

    def has_right_collision(self, element, element_before, state, objects=None):
        """Check if element has actual collision on the right side (overlap detection)."""
        if objects is None:
            objects = self.solid_objects

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        test_box_now = element.box.copy()
        test_box_before = element.box.copy()
        test_box_before.y = element_before.box.y

        for box in boxes:
            if box is element:
                continue
            if test_box_now.colliderect(box.box) or test_box_before.colliderect(
                box.box
            ):
                if (
                    test_box_now.right >= box.box.left
                    or test_box_before.right >= box.box.left
                ):
                    return True
        return False

    def has_left_collision(self, element, element_before, state, objects=None):
        """Check if element has actual collision on the left side (overlap detection)."""
        if objects is None:
            objects = self.solid_objects

        boxes = []
        for name in objects:
            boxes += state.boxes.get(name, [])

        test_box_now = element.box.copy()
        test_box_before = element.box.copy()
        test_box_before.y = element_before.box.y

        for box in boxes:
            if box is element:
                continue
            if test_box_now.colliderect(box.box) or test_box_before.colliderect(
                box.box
            ):
                if (
                    test_box_now.left <= box.box.right
                    or test_box_before.left <= box.box.right
                ):
                    return True
        return False

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
            if element.box.colliderect(box.box):
                if element.box.top > box.box.top:
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

    def has_x_collision_adjustment(self, player):
        return player.collision_info["x_adjusted"]

    def has_y_collision_adjustment(self, player):
        return player.collision_info["y_adjusted"]

    def has_collision_adjustment(self, player):
        """Return True if the player had any collision-induced adjustment this frame."""
        return self.has_x_collision_adjustment(
            player
        ) or self.has_y_collision_adjustment(player)

    def is_horizontal_pipe(self, element):
        """Return True if the element represents a horizontal pipe Mario can enter."""
        return element.name == "pipe" and element.box.width > element.box.height

    def collides_with_horizontal_pipe(self, element, state):
        """Return True if element overlaps a horizontal pipe entrance (side collision)."""
        if not element:
            return False

        for pipe in state.boxes.get("pipe", []):
            if pipe is element:
                continue
            if not self.is_horizontal_pipe(pipe):
                continue
            if not element.box.colliderect(pipe.box):
                continue
            if element.box.top > pipe.box.top:
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
