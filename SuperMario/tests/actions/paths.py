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
    ticks: list[int] = []
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
        if not self.ticks:
            self.ticks = [0]

    def __eq__(self, other):
        """Check if two paths are equal."""
        return self.hashes[-1] == other.hashes[-1]

    def append(self, input: actions.PressedKeys, state: actions.BehaviorState):
        self.input_sequence.append(input)
        self.scores.append(self._score(state))
        self.hashes.append(self._hash(self.input_sequence))
        self.deaths.append(self._death(state))
        self.ticks.append(state.current_time)

    def _hash(self, input_sequence):
        """Compute hash dynamically from input_sequence."""
        return hash(tuple(input_sequence))

    def _death(self, state):
        """Check if the player is dead in the current state."""
        if state.player is None:
            return False

        return state.player.dead

    def _score(self, state):
        """Score the path based on the player's position, level number, and time.

        Prefers paths that reach higher positions in shorter time.
        Time is calculated from input sequence length divided by fps.
        Score format: level(xxx)-position(xxxxx)-time(xxx)
        """
        if state.player is None:
            return 0

        # Get level number, default to 1 if not available
        level_num = state.level_num if state.level_num is not None else 1

        # Calculate time in seconds based on path frame count, not absolute game time
        # This ensures deterministic scoring regardless of game startup timing
        fps = current().context.fps
        # Subtract 1 to exclude the initial dummy frame added by __post_init__
        time_in_seconds = (len(self.input_sequence) - 1) // fps

        # Score structure using powers of 10:
        # level (3 digits) * 10^9 = xxx_000_000_000
        # x_pos (5 digits) * 10^3 = 000_xxxxx_000
        # time (3 digits) * 10^0 = 000_000_000_xxx

        level_score = level_num * 10**9
        position_score = state.player.x_pos * 10**3
        time_score = 999 - time_in_seconds

        return level_score + position_score + time_score

    def select_stop_index(self, weights=None):
        """Select a stop index for the path based on triangular distribution."""
        if weights is None:
            weights = {
                "low": 0.6,
                "high": 1.0,
                "mode": 0.98,
            }

        sequence_length = len(self.input_sequence)
        stop_fraction = random.triangular(**weights)
        return max(1, min(sequence_length, round(stop_fraction * sequence_length)))


class GamePaths(msgspec.Struct):
    paths: list[GamePath] = []

    def backtrack_path(self, path: GamePath, backtrack_frames: int = None):
        """Backtrack the path if the score before the dead state is higher than the best path.

        Args:
            path: The GamePath object to potentially backtrack
            backtrack_frames: Number of frames to backtrack, default is 60

        Returns:
            GamePath or None: Backtracked path if backtracking was performed, None otherwise
        """

        if backtrack_frames is None:
            backtrack_frames = current().context.backtrack

        if len(path.input_sequence) < (backtrack_frames + 1):
            return None

        note(
            f"Backtracking {backtrack_frames} frames for path with score: {path.scores[-1]}"
        )

        return GamePath(
            input_sequence=path.input_sequence[: -(backtrack_frames + 1)],
            scores=path.scores[: -(backtrack_frames + 1)],
            hashes=path.hashes[: -(backtrack_frames + 1)],
            ticks=path.ticks[: -(backtrack_frames + 1)],
        )

    def split_path(self, path: GamePath, backtrack_frames: int = None):
        """Split the path into two parts if in the middle of the path the score is higher than the best.

        Args:
            path: The GamePath object to potentially split
            paths: The GamePaths context containing all stored paths

        Returns:
            GamePath or None: Split path if splitting was performed, None otherwise
        """
        if not self.paths:
            return None

        backtracked_path = self.backtrack_path(path, backtrack_frames)

        if backtracked_path is None:
            return None

        note(f"Backtracked path for score: {backtracked_path.scores[-1]}")
        note(f"Backtracked path max score: {max(backtracked_path.scores)}")
        if max(backtracked_path.scores) >= backtracked_path.scores[-1]:
            split_index = backtracked_path.scores.index(max(backtracked_path.scores))
            return GamePath(
                input_sequence=backtracked_path.input_sequence[:split_index],
                scores=backtracked_path.scores[:split_index],
                hashes=backtracked_path.hashes[:split_index],
                ticks=backtracked_path.ticks[:split_index],
            )
        return None

    def add(self, path: GamePath):
        """Add a path to the paths list."""
        if path in self.paths:
            note(f"Path already exists for score: {path.scores[-1]}")
            return

        note(f"Trying to add path for score: {path.scores[-1]}")
        # Split the path into two parts if in the middle of the path the score is higher than the best
        split_path = self.split_path(path)
        if split_path is not None:
            if split_path not in self.paths:
                if not split_path.deaths[-1]:
                    if split_path not in self.paths:
                        note(f"Adding split path with score: {split_path.scores[-1]}")
                        self.paths.append(split_path)
            else:
                note(f"Split path already exists for score: {split_path.scores[-1]}")
        else:
            note(f"Split path is None for score: {path.scores[-1]}")

        if not path.deaths[-1]:
            note(f"Adding path with score: {path.scores[-1]}")
            self.paths.append(path)
        else:
            note(f"Skipping path as it leads to death for score: {path.scores[-1]}")

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

    def clean(self, score_threshold_px: int = 100) -> None:
        """Clean the paths list by collapsing paths with similar max scores.

        Paths whose max scores are within the threshold are considered similar,
        and only the highest scoring path from each group is kept.

        Args:
            score_threshold_px: Position difference threshold in pixels for grouping similar paths (default: 100)
        """
        score_threshold = score_threshold_px * 1000  # pixels * time_score

        if not self.paths:
            return

        # Sort paths by their max score (best first)
        self.sort()

        # Keep only paths that differ by more than the threshold
        cleaned_paths = []
        for path in self.paths:
            # Keep this path if it's not too similar to any already kept path
            if not any(
                abs(path.scores[-1] - kept.scores[-1]) <= score_threshold
                for kept in cleaned_paths
            ):
                cleaned_paths.append(path)

        removed = len(self.paths) - len(cleaned_paths)
        if removed > 0:
            note(
                f"Cleaned {removed} paths with similar scores (threshold: {score_threshold})"
            )

        self.paths = cleaned_paths
        note(f"Paths after cleaning: {len(self.paths)}")

    def select(self, best_path=False) -> Path:
        """Select a path from the paths list based on the score using exponential weighting.

        The best path (highest score) is selected ~70% of the time, with remaining probability
        distributed among other paths using exponential weighting.
        """
        if current().context.always_pick_best_path:
            best_path = True

        # Sort paths by score (best first)
        self.sort()

        scores = [path.scores[-1] for path in self.paths]

        # Display all scores
        note(f"All end scores: {scores}")
        note(f"Best end score: {scores[0]}")

        if best_path:
            return self.paths[0]

        # Use aggressive selection: ~70% for best path, rest distributed exponentially
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score or len(scores) == 1:
            # All scores are the same or only one path, select the first one
            weights = [1.0] * len(scores)
        else:
            # Assign 50% probability to the best path
            best_weight = 0.50

            # Distribute remaining 50% among all paths (including best) using exponential weighting
            # This gives the best path additional weight from the exponential distribution
            normalized_scores = [
                (s - min_score) / (max_score - min_score) for s in scores
            ]
            # Use exponential weighting for distribution
            scaling_factor = 5.0
            exp_weights = [math.exp(scaling_factor * ns) for ns in normalized_scores]

            # Normalize exponential weights to sum to 1.0
            total_exp_weight = sum(exp_weights)
            normalized_exp_weights = [w / total_exp_weight for w in exp_weights]

            # Combine: best path gets 70% + its share of remaining 30%
            weights = [
                best_weight + (1 - best_weight) * w for w in normalized_exp_weights
            ]
            # Adjust all other paths to only get their share of remaining 30%
            weights[0] = best_weight + (1 - best_weight) * normalized_exp_weights[0]
            for i in range(1, len(weights)):
                weights[i] = (1 - best_weight) * normalized_exp_weights[i]

        selected_idx = random.choices(range(len(self.paths)), weights=weights, k=1)[0]

        path = self.paths[selected_idx]
        note(f"Selected path score: {scores[selected_idx]} (index {selected_idx})")

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
