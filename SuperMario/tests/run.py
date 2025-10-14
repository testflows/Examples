#!/usr/bin/env python3

import os
import sys

from testflows.core import *

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Hides the pygame welcome message
append_path(sys.path, os.path.join(current_dir(), ".."), pos=0)

import actions.game
import models.game


def argparser(parser):
    """Add arguments to the parser."""
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="frames per second (default: 60)",
    )
    parser.add_argument(
        "--start-level",
        type=int,
        default=1,
        help="starting level (default: 1)",
    )
    parser.add_argument("--save-video", action="store_true", help="save video")
    parser.add_argument(
        "--play-seconds",
        type=int,
        default=30,
        help="duration for play in seconds (default: 30)",
    )

    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="run autonomous play (default: False)",
    )

    parser.add_argument(
        "--manual",
        action="store_true",
        help="run manual play (default: False)",
    )

    parser.add_argument(
        "--with-model",
        action="store_true",
        help="run with model (default: False)",
    )

    # Autonomous play
    parser.add_argument(
        "--paths-file",
        type=str,
        default="paths.json",
        help="path to paths file (default: paths.json)",
    )

    parser.add_argument(
        "--load-paths",
        action="store_true",
        help="load paths from file (default: False)",
    )

    parser.add_argument(
        "--save-paths",
        action="store_true",
        default=False,
        help="save paths to file (default: False)",
    )

    parser.add_argument(
        "--play-best-path",
        action="store_true",
        help="play the best path (default: False)",
    )

    parser.add_argument(
        "--always-pick-full-path",
        action="store_true",
        help="always pick the full path (default: False)",
    )

    parser.add_argument(
        "--always-pick-best-path",
        action="store_true",
        help="always pick the best path (default: False)",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=20,
        help="interval for autonomous play in seconds (default: 20)",
    )

    parser.add_argument(
        "--tries",
        type=int,
        default=3,
        help="number of tries for autonomous play (default: 3)",
    )

    parser.add_argument(
        "--backtrack",
        type=int,
        default=None,
        help="number of frames to backtrack (default: None)",
    )


@TestModule
@Name("super mario")
@ArgumentParser(argparser)
def module(
    self,
    fps=60,
    start_level=1,
    save_video=False,
    with_model=False,
    play_seconds=30,
    manual=False,
    autonomous=False,
    paths_file="paths.json",
    load_paths=False,
    save_paths=False,
    play_best_path=False,
    always_pick_full_path=False,
    always_pick_best_path=False,
    interval=20,
    tries=3,
    backtrack=None,
):
    """Run tests for the Super Mario Bros. game."""

    if play_best_path:
        play_seconds = 1
        interval = 1
        tries = 1
        save_paths = False
        always_pick_full_path = True
        always_pick_best_path = True

    self.context.fps = fps
    self.context.start_level = start_level
    self.context.save_video = save_video
    self.context.video_writer = None
    self.context.model = None
    self.context.always_pick_full_path = always_pick_full_path
    self.context.always_pick_best_path = always_pick_best_path
    self.context.backtrack = backtrack if backtrack is not None else fps * 1

    if not autonomous:
        with Given("start the game"):
            self.context.game = actions.game.start()

        if with_model:
            with Given("create game model"):
                self.context.model = models.game.Game(self.context.game)

    if manual:
        with Feature("manual"):
            Scenario("play", test=load("tests.manual_play", "scenario"))(
                play_seconds=play_seconds
            )

    elif autonomous:
        with Feature("autonomous"):
            Scenario("play", test=load("tests.autonomous_play", "scenario"))(
                play_seconds=play_seconds,
                with_model=with_model,
                paths_file=paths_file,
                load_paths=load_paths,
                save_paths=save_paths,
                interval=interval,
                tries=tries,
            )

    elif with_model:
        with Feature("with model"):
            Scenario("move right", run=load("tests.move_right_with_model", "scenario"))
            Scenario("move left", run=load("tests.move_left_with_model", "scenario"))
            Scenario("dont move", run=load("tests.dont_move_with_model", "scenario"))
            Scenario("move jump", run=load("tests.move_jump_with_model", "scenario"))

    else:
        with Feature("classic"):
            Scenario("move right", run=load("tests.move_right", "scenario"))
            Scenario("move left", run=load("tests.move_left", "scenario"))
            Scenario("move jump", run=load("tests.move_jump", "scenario"))


if main():
    module()
