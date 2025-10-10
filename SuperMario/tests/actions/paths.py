import os
import math
import random
import msgspec

from testflows.core import *

import actions.game as actions

Path = list[actions.PressedKeys]


class GamePath(msgspec.Struct):
    """A path in the game."""

    input_sequence: list[actions.PressedKeys] = []
    scores: list[int] = []
    hashes: list[int] = []
    deaths: list[bool] = []

    def __post_init__(self):
        if not self.input_sequence:
            self.input_sequence = [
                actions.PressedKeys(left=0, right=0, down=0, jump=0, action=0, enter=0)
            ]
        if not self.scores:
            self.scores = [0]
        if not self.hashes:
            self.hashes = [0]
        if not self.deaths:
            self.deaths = [False]

    def append(self, input: actions.PressedKeys, state: actions.BehaviorState):
        self.input_sequence.append(input)
        self.scores.append(self._score(state))
        self.hashes.append(self._hash(self.input_sequence))
        self.deaths.append(self._death(state))

    def _hash(self, input_sequence):
        """Compute hash dynamically from input_sequence."""
        return hash(tuple(input_sequence))

    def _death(self, state):
        """Check if the player is dead in the current state."""
        if state.player is None:
            return False

        return state.player.dead

    def _score(self, state):
        """Score the path based on the player's position and level number."""
        if state.player is None:
            return 0

        # Get level number, default to 1 if not available
        level_num = state.level_num if state.level_num is not None else 1

        # Weight level number much higher than x position
        # Assuming max x position is around 3000-4000 pixels per level
        # Level weight of 100000 ensures level progression dominates scoring
        level_score = level_num * 100000
        position_score = state.player.x_pos

        return level_score + position_score


class GamePaths(msgspec.Struct):
    paths: list[GamePath] = []

    def backtrack_path(self, path: GamePath, backtrack_frames: int = 60):
        """Backtrack the path if the score before the dead state is higher than the best path.

        Args:
            path: The GamePath object to potentially backtrack
            backtrack_frames: Number of frames to backtrack, default is 60

        Returns:
            GamePath or None: Backtracked path if backtracking was performed, None otherwise
        """
        if len(path.input_sequence) < (backtrack_frames * 2):
            return None

        return GamePath(
            input_sequence=path.input_sequence[:-backtrack_frames],
            scores=path.scores[:-backtrack_frames],
            hashes=path.hashes[:-backtrack_frames],
        )

    def split_path(self, path: GamePath, backtrack_frames: int = 120):
        """Split the path into two parts if in the middle of the path the score is higher than the best.

        Args:
            path: The GamePath object to potentially split
            paths: The GamePaths context containing all stored paths

        Returns:
            GamePath or None: Split path if splitting was performed, None otherwise
        """
        if not self.paths:
            return None

        path = self.backtrack_path(path, backtrack_frames)

        if path is None:
            return None

        if max(path.scores) > path.scores[-1]:
            split_index = path.scores.index(max(path.scores))
            if split_index != len(path.input_sequence) - 1:
                return GamePath(
                    input_sequence=path.input_sequence[:split_index],
                    scores=path.scores[:split_index],
                    hashes=path.hashes[:split_index],
                )
        return None

    def add(self, path: GamePath):
        """Add a path to the paths list."""
        if path in self.paths:
            return

        # Split the path into two parts if in the middle of the path the score is higher than the best
        split_path = self.split_path(path)
        if split_path is not None:
            if split_path not in self.paths:
                note(f"Adding split path with score: {split_path.scores[-1]}")
                self.paths.append(split_path)

        if not path.deaths[-1]:
            note(f"Adding path with score: {path.scores[-1]}")
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
        self.paths.sort(key=lambda x: x.scores[-1], reverse=True)

    def delete(self, path: GamePath) -> None:
        """Delete a path from the paths list."""
        if path in self.paths:
            note(f"Deleting path with score: {path.scores[-1]}")
            self.paths.remove(path)

    def select(self) -> Path:
        """Select a path from the paths list based on the score using exponential weighting."""
        # Sort paths by score (best first)
        self.sort()

        scores = [path.scores[-1] for path in self.paths]

        # Display all scores
        note(f"All end scores: {scores}")
        note(f"Best end score: {scores[0]}")

        # Use exponential weighting - best score gets exponentially higher probability
        min_score = min(scores)
        max_score = max(scores)

        # Scale scores to prevent overflow: normalize to [0, 1] then apply exponential
        if max_score == min_score:
            # All scores are the same, use uniform distribution
            weights = [1.0] * len(scores)
        else:
            # Normalize scores to [0, 1] range, then apply exponential with scaling factor
            normalized_scores = [
                (s - min_score) / (max_score - min_score) for s in scores
            ]
            # Use high scaling factor for very strong bias toward best score
            scaling_factor = 8.0  # Much higher bias toward best score
            weights = [math.exp(scaling_factor * ns) for ns in normalized_scores]

        selected_idx = random.choices(range(len(self.paths)), weights=weights, k=1)[0]

        path = self.paths[selected_idx]
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
