import pygame as pg

from copy import deepcopy
from contextlib import contextmanager
from source import tools
from source import constants as c
from source.states import main_menu, load_screen, level
from PIL import Image

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
    def __init__(self, keys, boxes, viewport, frame):
        self.keys = deepcopy(keys)
        self.boxes = boxes
        self.viewport = deepcopy(viewport)
        self.frame = frame

    def __str__(self):
        return f"BehaviorState(keys={self.keys}, boxes={self.boxes}, viewport={self.viewport}, frame=...)"

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

    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
            elif event.type == pg.KEYDOWN:
                if self.manual:
                    pressed = pg.key.get_pressed()
                    for code in all_key_codes:
                        if pressed[code]:
                            self.keys[code] = True
                else:
                    if hasattr(event, "key"):
                        self.keys[event.key] = True
            elif event.type == pg.KEYUP:
                if self.manual:
                    pressed = pg.key.get_pressed()
                    for code in all_key_codes:
                        if code in self.keys and not pressed[code]:
                            del self.keys[code]
                else:
                    if hasattr(event, "key"):
                        del self.keys[event.key]

    def main(self):
        """Main game loop."""

        def _main():
            while not self.done:
                self.event_loop()
                self.update()
                self.vision.detect()
                self.behavior.append(
                    BehaviorState(
                        self.keys,
                        self.vision.boxes,
                        self.vision.viewport,
                        pg.surfarray.array3d(self.screen),
                    )
                )
                yield self
                pg.display.update()
                self.clock.tick(self.fps)

        self.play = _main()


@contextmanager
def simulate_keypress(key):
    """Simulate a key press and release event for the given key."""
    keydown_event = pg.event.Event(pg.KEYDOWN, key=key)
    pg.event.post(keydown_event)
    yield
    keyup_event = pg.event.Event(pg.KEYUP, key=key)
    pg.event.post(keyup_event)


def press_enter():
    """Press the enter key."""
    return simulate_keypress(key=keys["enter"])


def press_right():
    """Press the right arrow key."""
    return simulate_keypress(key=keys["right"])


def press_left():
    """Press the left arrow key."""
    return simulate_keypress(key=keys["left"])


def press_down():
    """Press the down arrow key."""
    return simulate_keypress(key=keys["down"])


def press_jump():
    """Press the jump key."""
    return simulate_keypress(key=keys["jump"])


def press_action():
    """Press the action key."""
    return simulate_keypress(keys["action"])


def play(game, seconds=1, frames=None, model=None):
    """Play the game for the specified number seconds or frames."""
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


def save_video(game, path="output.gif", start=0):
    """Save the video of the game's behavior."""
    frames = []
    for state in game.behavior[start:]:
        image = Image.fromarray(state.frame)
        image = image.transpose(Image.Transpose.ROTATE_270)
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        frames.append(image)
    frames += [frames[-1]] * 30  # add a delay at the end of the video
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0)


@TestStep(When)
def wait_ready(self, game, seconds=3):
    """Wait for game to be loaded and ready."""
    next(game.play)

    with press_enter():
        next(game.play)

    for _ in range(seconds * game.fps):
        next(game.play)


@TestStep(Given)
def start(self, ready=True):
    """Start the game and wait for it to be ready."""

    game = Control()

    state_dict = {
        c.MAIN_MENU: main_menu.Menu(),
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
        pg.quit()
