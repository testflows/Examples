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


@TestModule
@Name("super mario")
@ArgumentParser(argparser)
def module(self, save_video=False):
    """Run tests for the Super Mario Bros. game."""

    self.context.save_video = save_video

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
        pass
        # Scenario("move jump", run=load("tests.move_jump_with_model", "scenario"))
        # Scenario("move right", run=load("tests.move_right_with_model", "scenario"))
        # Scenario("move left", run=load("tests.move_left_with_model", "scenario"))
        # Scenario("dont move", run=load("tests.dont_move_with_model", "scenario"))


if main():
    module()
