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
        "--manual-play-seconds",
        type=int,
        default=30,
        help="duration for manual play in seconds (default: 30)",
    )
    parser.add_argument(
        "--autonomous-play-seconds",
        type=int,
        default=30,
        help="duration for autonomous play in seconds (default: 30)",
    )


@TestModule
@Name("super mario")
@ArgumentParser(argparser)
def module(self, save_video=False, manual_play_seconds=30, autonomous_play_seconds=30):
    """Run tests for the Super Mario Bros. game."""

    self.context.save_video = save_video
    self.context.manual_play_seconds = manual_play_seconds

    with Given("start the game"):
        self.context.game = actions.game.start()

    with And("create game model"):
        self.context.model = models.game.Game(self.context.game)

    with And("play the game for 3 frames"):
        actions.game.play(self.context.game, frames=3, model=self.context.model)

    with Feature("classic"):
        Scenario("move right", run=load("tests.move_right", "scenario"))
        Scenario("move left", run=load("tests.move_left", "scenario"))
        Scenario("move jump", run=load("tests.move_jump", "scenario"))

    with Feature("with model"):
        Scenario("move right", run=load("tests.move_right_with_model", "scenario"))
        Scenario("move left", run=load("tests.move_left_with_model", "scenario"))
        Scenario("dont move", run=load("tests.dont_move_with_model", "scenario"))
        Scenario("move jump", run=load("tests.move_jump_with_model", "scenario"))

    with Feature("manual"):
        Scenario("play", test=load("tests.manual_play", "scenario"))(
            play_seconds=manual_play_seconds
        )

    with Feature("autonomous"):
        Scenario("play", test=load("tests.autonomous_play", "scenario"))(
            play_seconds=autonomous_play_seconds
        )


if main():
    module()
