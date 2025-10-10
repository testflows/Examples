#! /usr/bin/env python3

import os
import sys

from testflows.core import *

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Hides the pygame welcome message
append_path(sys.path, os.path.join(current_dir(), ".."), pos=0)

import actions.game
import models.game


def argparser(parser):
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


@TestModule
@Name("super mario")
@ArgumentParser(argparser)
def module(
    self,
    save_video=False,
    with_model=False,
    play_seconds=30,
    manual=False,
    autonomous=False,
    paths_file="paths.json",
    load_paths=False,
    save_paths=False,
):
    """Run tests for the Super Mario Bros. game."""

    self.context.save_video = save_video
    self.context.model = None

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
