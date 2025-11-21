import msgspec
import pygame as pg
import imageio.v2 as imageio
import numpy as np

from copy import deepcopy
from contextlib import contextmanager
from source import tools
from source import constants as c
from source.states import main_menu, load_screen, level

from testflows.core import *
from .vision import Vision

# Define keybindings
keys = {
    "action": pg.K_s,
    "jump": pg.K_a,
    "left": pg.K_LEFT,
    "right": pg.K_RIGHT,
    "down": pg.K_DOWN,
    "enter": pg.K_RETURN,
}

all_key_codes = [code for name, code in vars(pg).items() if name.startswith("K_")]


class PressedKeys(msgspec.Struct):
    right: int = 0
    left: int = 0
    jump: int = 0
    action: int = 0
    down: int = 0
    enter: int = 0

    def __hash__(self):
        """Make PressedKeys hashable by returning hash of tuple of field values."""
        return hash(
            (self.right, self.left, self.jump, self.action, self.down, self.enter)
        )


class Player:
    """Encapsulates player state data for easy access."""

    def __init__(self, player):
        # Extract attributes from player object
        attributes = [
            "x_vel",
            "y_vel",
            "state",
            "big",
            "fire",
            "dead",
            "invincible",
            "hurt_invincible",
            "walking_timer",
            "current_time",
            "frame_index",
            "collision_info",
        ]

        for attr in attributes:
            setattr(self, attr, getattr(player, attr, None))

        self.x_pos = player.rect.x
        self.y_pos = player.rect.y
        self.collision_info = player.collision_info.to_dict()

    def __str__(self):
        return (
            f"Player(x_vel={self.x_vel}, "
            f"y_vel={self.y_vel}, "
            f"state='{self.state}', "
            f"big={self.big}, "
            f"dead={self.dead}, "
            f"collision_info={self.collision_info})"
        )

    def __repr__(self):
        return str(self)


class Keys:
    def __init__(self):
        self.keys = {}

    def key_code(self, name):
        return pg.key.key_code(name)

    def key_name(self, key):
        return pg.key.name(key)

    def __contains__(self, key):
        return key in self.keys

    def __getitem__(self, key):
        if key in self.keys:
            return self.keys[key]
        return False

    def __setitem__(self, key, value):
        self.keys[key] = value

    def __delitem__(self, key):
        del self.keys[key]

    def __str__(self):
        return f"Keys({','.join([self.key_name(key) for key in self.keys])})"


class BehaviorState:
    def __init__(self, keys, boxes, viewport, frame, state):
        self.keys = deepcopy(keys)
        self.boxes = boxes
        self.frame = None
        if current().context.video_writer:
            frame = np.rot90(
                frame, k=-1
            )  # Rotate 270° counter-clockwise (90° clockwise)
            frame = np.fliplr(frame)  # Flip horizontally
            current().context.video_writer.append_data(frame)
        self.player = None
        self.level_num = None
        self.start_x = None
        self.end_x = None
        self.current_time = 0
        if viewport:
            self.viewport = (viewport.x, viewport.y, viewport.w, viewport.h)
        else:
            self.viewport = None

        # Extract player state
        if hasattr(state, "player"):
            self.player = Player(state.player)

        if hasattr(state, "persist"):
            self.level_num = state.persist.get("level num")
            self.current_time = int(state.persist.get("current time") // 1000)

        if hasattr(state, "start_x"):
            self.start_x = state.start_x

        if hasattr(state, "end_x"):
            self.end_x = state.end_x

    def __str__(self):
        return (
            f"BehaviorState(level_num={self.level_num}, "
            f"keys={self.keys}, "
            f"boxes={self.boxes}, "
            f"player={self.player}, "
            f"start_x={self.start_x}, "
            f"end_x={self.end_x}, "
            f"viewport={self.viewport}, "
            f"current_time={self.current_time})"
        )

    def __repr__(self):
        return str(self)


class Control(tools.Control):
    def __init__(self, fps=60, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fps = fps
        self.keys = Keys()
        self.screen = pg.display.get_surface()
        self.vision = Vision(self)
        self.behavior = []
        self.play = None
        self.manual = False
        self.ticks = 0

    def update(self):
        self.current_time = self.ticks * 1000 // self.fps
        if self.state.done:
            self.flip_state()
        self.state.update(self.screen, self.keys, self.current_time)

    def event_loop(self):
        if self.manual:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.done = True
                elif event.type in (pg.KEYDOWN, pg.KEYUP):
                    pressed = pg.key.get_pressed()
                    new_keys = Keys()
                    for code in all_key_codes:
                        if pressed[code]:
                            new_keys[code] = True
                    self.keys = new_keys
        else:
            # In automated mode, clear event queue without processing
            # This prevents stray events from affecting deterministic execution
            pg.event.clear()

    def main(self):
        """Main game loop."""

        def _main():
            while not self.done:
                self.event_loop()
                self.update()
                self.vision.detect()

                self.behavior.append(
                    BehaviorState(
                        keys=self.keys,
                        boxes=self.vision.boxes,
                        viewport=self.vision.viewport,
                        frame=pg.surfarray.array3d(self.screen),
                        state=self.state,
                    )
                )
                yield self
                pg.display.update()
                self.clock.tick(self.fps)
                self.ticks += 1

        self.play = _main()


@contextmanager
def simulate_keypress(game, key):
    """Simulate a key press and release."""
    game.keys[key] = True
    yield
    del game.keys[key]


def is_key_pressed(game, key):
    """Return True if the given key is pressed in the state."""
    return 1 if game.keys.key_code(key) in game.keys else 0


def get_pressed_keys(game):
    """Extract currently pressed keys from game."""

    return PressedKeys(
        right=is_key_pressed(game, "right"),
        left=is_key_pressed(game, "left"),
        jump=is_key_pressed(game, "a"),
        action=is_key_pressed(game, "s"),
        down=is_key_pressed(game, "down"),
        enter=is_key_pressed(game, "enter"),
    )


def press_keys(game, press: PressedKeys, pressed_keys: PressedKeys = None):
    """Update which keys are currently pressed."""
    if pressed_keys is None:
        pressed_keys = get_pressed_keys(game)

    for key_name in press.__struct_fields__:
        pressed = getattr(press, key_name)
        current = getattr(pressed_keys, key_name)
        if pressed and not current:
            game.keys[keys[key_name]] = True
        elif not pressed and current:
            del game.keys[keys[key_name]]


def press_enter(game):
    """Press the enter key."""
    return simulate_keypress(game, key=keys["enter"])


def press_right(game):
    """Press the right arrow key."""
    return simulate_keypress(game, key=keys["right"])


def press_left(game):
    """Press the left arrow key."""
    return simulate_keypress(game, key=keys["left"])


def press_down(game):
    """Press the down arrow key."""
    return simulate_keypress(game, key=keys["down"])


def press_jump(game):
    """Press the jump key."""
    return simulate_keypress(game, key=keys["jump"])


def press_action(game):
    """Press the action key."""
    return simulate_keypress(game, keys["action"])


def play(game, seconds=1, frames=None, model=None):
    """Play the game for the specified number of seconds or frames."""
    if frames is None:
        frames = int(seconds * game.fps)

    for i in range(frames):
        next(game.play)
        if model:
            model.expect(game.behavior)


def get_elements(game, name, frame=-1):
    """Get elements by name in the specified frame, default: -1 (current frame)."""
    return game.behavior[frame].boxes[name]


def get_element(game, name, frame=-1):
    """Get element by name in the specified frame, default: -1 (current frame)."""
    return get_elements(game, name, frame)[0]


def overlay(game, elements, color=Vision.color["red"]):
    """Overlay boxes of elements on the screen."""
    game.vision.overlay(boxes=[element.box for element in elements], color=color)
    # update game's last frame with the overlay
    game.behavior[-1].frame = pg.surfarray.array3d(game.screen)


def save_video2(game, path="output.gif", start=0):
    with imageio.get_writer(path, mode="I", duration=1 / 30) as writer:
        for state in game.behavior[start:]:
            writer.append_data(state.frame)

        for _ in range(30):  # freeze last frame
            writer.append_data(state.frame)


@TestStep(When)
def wait_ready(self, game, seconds=3):
    """Wait for game to be loaded and ready."""
    next(game.play)

    with press_enter(game):
        next(game.play)

    for _ in range(seconds * game.fps):
        next(game.play)
    note(f"Game ready after { game.ticks } ticks")


@TestStep(Given)
def start(self, ready=True, quit=True, fps=None, start_level=None):
    """Start the game and wait for it to be ready.

    Args:
        ready: Wait for game to be ready before yielding
        quit: Quit pygame when done
        fps: Frames per second
        start_level: Starting level number (default: None, uses level 1)
    """
    if fps is None:
        fps = self.context.fps

    if start_level is None:
        start_level = self.context.start_level

    game = Control(fps=fps)

    state_dict = {
        c.MAIN_MENU: main_menu.Menu(start_level=start_level),
        c.LOAD_SCREEN: load_screen.LoadScreen(),
        c.LEVEL: level.Level(),
        c.GAME_OVER: load_screen.GameOver(),
        c.TIME_OUT: load_screen.TimeOut(),
    }

    game.setup_states(state_dict, c.MAIN_MENU)
    try:
        game.main()
        if ready:
            wait_ready(game=game)
        yield game
    finally:
        if quit:
            with By("quitting game"):
                pg.quit()


@TestStep(Given)
def setup(self, game, overlays=None):
    """Common test setup and cleanup."""
    overlays = overlays or []
    base_frame = len(game.behavior)
    try:
        if current().context.save_video:
            path = f"{name.basename(self.parent.name).replace(' ', '_')}.mp4"
            current().context.video_writer = imageio.get_writer(
                path,
                fps=game.fps,
                codec="libx264",
                quality=8,
                macro_block_size=1,
            ).__enter__()
        yield
    finally:
        if overlays:
            with By("drawing overlays"):
                overlay(
                    game,
                    [
                        get_element(
                            game,
                            name,
                            frame=(base_frame + offset) if offset > -1 else offset,
                        )
                        for name, offset in overlays
                    ],
                )
        if current().context.save_video:
            current().context.video_writer.__exit__(None, None, None)
