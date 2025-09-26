import pygame as pg

from dataclasses import dataclass


@dataclass
class Element:
    name: str
    box: pg.Rect
    id: int


class Vision:
    """Object detection."""

    color = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "gray": (128, 128, 128),
        "pink": (255, 192, 203),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
    }

    def __init__(self, game):
        self.game = game
        self.boxes = {}
        self.viewport = pg.Rect(0, 0, 0, 0)

    def overlay(self, boxes=None, color=(255, 0, 0), thickness=3, adjust=True):
        """Overlay boxes directly on the screen."""
        screen = self.game.screen

        if boxes is None:
            visible = self.get_visible()
            boxes = [box for element in visible for box in visible[element]]

        for box in boxes:
            if adjust:
                box = self.adjust_box(box, self.viewport)
            x1, y1, w, h = map(int, box)
            # Draw a rectangle directly on the screen
            pg.draw.rect(screen, color, pg.Rect(x1, y1, w, h), thickness)

        # Update the Pygame display
        pg.display.flip()  # Refresh the screen to show the changes

    def get_visible(self):
        """
        Get all currently visible elements on the screen.

        Returns:
            list: List of visible sprites.
        """
        visible = []

        if self.game.state_name != "level":
            # Return an empty set if the state is not "level"
            return {}

        sprite_group = []
        viewport = self.game.state.viewport

        for attr_name in vars(self.game.state):
            attr = getattr(self.game.state, attr_name)
            if isinstance(attr, pg.sprite.Sprite):
                sprite_group.append(attr)
            elif isinstance(attr, pg.sprite.Group):
                sprite_group += [sprite for sprite in attr]

        for sprite in sprite_group:
            if viewport.colliderect(sprite.rect):
                visible.append(sprite)

        boxes = {}
        for sprite in set(visible):
            name = sprite.__class__.__name__.lower()
            # remove checkpoints
            if name == "checkpoint":
                continue
            if name not in boxes:
                boxes[name] = []
            x, y, w, h = sprite.rect
            rect = pg.Rect(x, y, w, h)
            boxes[name].append(Element(name, rect, id(sprite)))

        return boxes

    def top_touch(self, box1, box2, tolerance=0):
        """
        Check if box1's top edge touches box2's bottom edge within a given tolerance.

        Args:
            box1 (pg.Rect): The first rectangle.
            box2 (pg.Rect): The second rectangle.
            tolerance (int, optional): The allowable deviation in pixels. Defaults to 0.

        Returns:
            bool: True if box1's top edge is within the tolerance of box2's bottom edge and the rectangles horizontally overlap.
        """
        # Calculate horizontal overlap width
        horizontal_overlap = min(box1.right, box2.right) - max(box1.left, box2.left)
        # Check if bottom edge is within the tolerance and if there is any horizontal overlap
        return (abs(box1.top - box2.bottom) <= tolerance) and (horizontal_overlap > 0)

    def bottom_touch(self, box1, box2, tolerance=0):
        """
        Check if box1's bottom edge touches box2's top edge within a given tolerance.

        Args:
            box1 (pg.Rect): The first rectangle.
            box2 (pg.Rect): The second rectangle.
            tolerance (int, optional): The allowable deviation in pixels for vertical alignment. Defaults to 0.

        Returns:
            bool: True if box1's bottom edge is within the tolerance of box2's top edge
                and there is horizontal overlap, False otherwise.
        """
        # Calculate horizontal overlap width
        horizontal_overlap = min(box1.right, box2.right) - max(box1.left, box2.left)
        # Check if bottom edge is within the tolerance and if there is any horizontal overlap
        return (abs(box1.bottom - box2.top) <= tolerance) and (horizontal_overlap > 0)

    def right_touch(self, box1, box2, tolerance=0):
        """
        Check if box1's right edge touches box2's left edge within a given tolerance.

        Args:
            box1 (pg.Rect): The first rectangle.
            box2 (pg.Rect): The second rectangle.
            tolerance (int, optional): Allowable deviation in pixels for horizontal alignment. Defaults to 0.

        Returns:
            bool: True if box1's right edge is within the tolerance of box2's left edge
                and there is a positive vertical overlap, False otherwise.
        """
        # Check if the horizontal edges are touching within the tolerance.
        horizontal_touch = abs(box1.right - box2.left) <= tolerance
        # Calculate vertical overlap
        vertical_overlap = min(box1.bottom, box2.bottom) - max(box1.top, box2.top)

        return horizontal_touch and (vertical_overlap > 0)

    def left_touch(self, box1, box2, tolerance=0):
        """
        Check if box1's left edge touches box2's right edge within a given tolerance.

        Args:
            box1 (pg.Rect): The first rectangle.
            box2 (pg.Rect): The second rectangle.
            tolerance (int, optional): Allowable deviation in pixels for horizontal alignment. Defaults to 0.

        Returns:
            bool: True if box1's left edge is within the tolerance of box2's right edge
                and there is a positive vertical overlap, False otherwise.
        """
        # Check if the horizontal edges are touching within the tolerance.
        horizontal_touch = abs(box1.left - box2.right) <= tolerance
        # Calculate vertical overlap.
        vertical_overlap = min(box1.bottom, box2.bottom) - max(box1.top, box2.top)

        return horizontal_touch and (vertical_overlap > 0)

    def collides(self, box1, box2):
        """
        Check if two rectangles overlap (same logic as pygame's colliderect).

        Args:
            box1 (pg.Rect): The first rectangle.
            box2 (pg.Rect): The second rectangle.

        Returns:
            bool: True if the rectangles overlap, False otherwise.
        """
        return (
            box1.left < box2.right
            and box1.right > box2.left
            and box1.top < box2.bottom
            and box1.bottom > box2.top
        )

    def adjust_box(self, box, viewport):
        """Adjust the box coordinates to the viewport."""
        x, y, w, h = box
        # adjust the coordinates to the viewport
        # taking into account visible width
        if x < viewport.x:
            w = (x + w) - viewport.x
            x = 0
        else:
            x = x - viewport.x
            w = min(w, viewport.x + viewport.w - x)
        # keep y and height the same
        y = y
        h = h
        return pg.Rect(x, y, w, h)

    def in_view(self, box, viewport):
        """Check if the box is in the current viewport."""
        return viewport.colliderect(box)

    def detect(self):
        """Detect visible game elements."""
        self.boxes = self.get_visible()
        if self.boxes:
            self.viewport = self.game.state.viewport
        return self
