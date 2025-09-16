class Model:
    """Base model class."""

    def __init__(self, game):
        self.game = game

    def get(self, name, state):
        """Find element in the specified state."""
        elements = state.boxes.get(name, [])
        element = elements[0] if elements else None
        return element

    def get_mario(self, state):
        """Find Mario in the specified state."""
        return self.get("player", state)

    def is_key_pressed(self, state, key):
        """Return True if the given key is pressed in the state."""
        return state.keys.key_code(key) in state.keys

    def has_collision(self, element, state, direction, objects=None):
        """
        Check if the element has a collision with another object in a given direction.

        Args:
            game: The game context (used for overlay drawing).
            element: The element to check collisions for.
            state: The game state, which contains state.boxes (a dictionary mapping keys to lists of box objects).
            direction (str): One of "left", "right", "top", or "bottom".
            objects (iterable, optional): Specific keys from state.boxes to check. If None, all keys are used.

        Returns:
            bool: True if the element collides in the specified direction, False otherwise.
        """
        # Mapping from direction to the corresponding collision detection function.
        collision_funcs = {
            "left": self.game.vision.left_touch,
            "right": self.game.vision.right_touch,
            "top": self.game.vision.top_touch,
            "bottom": self.game.vision.bottom_touch,
        }

        if direction not in collision_funcs:
            raise ValueError(
                "Invalid direction. Must be one of 'left', 'right', 'top', or 'bottom'."
            )

        collision_func = collision_funcs[direction]

        # Gather all boxes from state.boxes based on the provided keys (or all keys if none provided)
        boxes = []
        if objects is None:
            objects = state.boxes.keys()
        for name in objects:
            boxes += state.boxes.get(name, [])

        # Check each box for a collision.
        for box in boxes:
            if box is element:
                continue

            if collision_func(element.box, box.box):
                self.game.vision.overlay(boxes=[element.box, box.box])
                return True

        return False
