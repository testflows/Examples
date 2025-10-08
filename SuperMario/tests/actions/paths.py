import os
import random
import msgspec

from testflows.core import *

import actions.game as actions

Path = list[actions.PressedKeys]


class GamePath(msgspec.Struct):
    """A path in the game."""

    input_sequence: list[actions.PressedKeys]
    score: int
    hash: int

    @classmethod
    def hash_path(cls, input_sequence):
        """Compute hash dynamically from input_sequence."""
        return hash(tuple(input_sequence))

    @classmethod
    def score_path(cls, behavior):
        """Score the path based on the player's position."""
        now = behavior[-1]
        if now.player is None:
            return 0
        return now.player.x_pos


class GamePaths(msgspec.Struct):
    paths: list[GamePath]

    def add(self, path: GamePath):
        """Add a path to the paths list."""
        self.paths.append(path)

    @classmethod
    def load(cls, filename: str) -> "GamePaths":
        """Load paths from a JSON file."""
        with open(filename, "rb") as f:
            return msgspec.json.decode(f.read(), type=cls)

    def save(self, filename: str) -> None:
        """Save paths to a JSON file."""
        with open(filename, "wb") as f:
            f.write(msgspec.json.encode(self))

    def sort(self) -> None:
        """Sort the paths based on the score. Highest score first."""
        self.paths.sort(key=lambda x: x.score, reverse=True)

    def select(self) -> Path:
        """Select a path from the paths list based on the score."""
        if not self.paths:
            return []

        scores = [path.score for path in self.paths]

        # Display all scores
        note(f"All scores: {scores}")
        note(f"Best score: {scores[0]}")

        # Pick path using probability distribution - higher scores more likely
        min_score = min(scores)
        weights = [s - min_score + 1 for s in scores]  # +1 to avoid zero weights
        selected_idx = random.choices(range(len(self.paths)), weights=weights, k=1)[0]

        path = self.paths[selected_idx].input_sequence
        note(f"Selected path score: {scores[selected_idx]}")

        return path


@TestStep(Given)
def load(self, filename):
    """Load paths from a JSON file."""
    # On first iteration, load existing paths if requested

    if not os.path.exists(filename):
        note(f"No paths file found at {filename}")
        return GamePaths(paths=[])

    self.context.paths = GamePaths.load(filename=filename)
    note(f"Loaded {len(self.context.paths.paths)} paths from {filename}")


@TestStep(Finally)
def save(self, filename):
    """Save paths to a JSON file."""
    self.context.paths.save(filename=filename)
