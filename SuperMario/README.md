# 🍄 Testing Super Mario Bros. Using a Behavior Model 

This is a [TestFlows](https://testflows.com) example that demonstrates automated testing of a Super Mario Bros. game. The project includes a playable Super Mario Bros. game built with Pygame and automated tests that use a behavior model to test the game.

## 👨‍💻 Credits

* Original game code: https://github.com/marblexu/PythonSuperMario
* Based on: https://github.com/justinmeister/Mario-Level-1

## 📚 References

* [Testing Super Mario Using a Behavior Model (Part 1)](https://testflows.com/blog/testing-super-mario-using-a-behavior-model-part1/).
  Covers the game’s architecture and the setup of a comprehensive testing framework.

* [Testing Super Mario Using a Behavior Model (Part 2)](https://testflows.com/blog/testing-super-mario-using-a-behavior-model-part2/).
  Delves into the theory behind behavior models and its application in testing.

## 📋 Prerequisites

```bash
pip3 install -r requirements.txt
```

## 🎮 Running the game

```bash
python3 main.py
```

### 🕹️ How to play

* use `LEFT`/`RIGHT`/`DOWN` key to control player
* use key `a` to jump
* use key `s` to shoot firewall or run

## 🧪 Running the tests

### 🎯 Classical Tests (Default)
Run basic movement tests without model:
```bash
python3 tests/run.py
```

### 🤖 Tests with Model
Run tests using the behavior model:
```bash
python3 tests/run.py --with-model
```

### 🎮 Manual Play
Play manually without and with model:
```bash
python3 tests/run.py --manual
```

```bash
python3 tests/run.py --manual --with-model
```

### 🤖 Autonomous Play
Run autonomous play without and with model:
```bash
python3 tests/run.py --autonomous
```

```bash
python3 tests/run.py --autonomous --with-model
```

```bash
python3 tests/run.py --autonomous --play-seconds 300
```

### 📁 Path Management
Load existing paths for autonomous play:
```bash
python3 tests/run.py --autonomous --load-paths
```

Load and save paths with custom file:
```bash
python3 tests/run.py --autonomous --load-paths --save-paths --paths-file custom_paths.json
```

> ⚠️ **Warning**: Save paths during autonomous play (will overwrite the existing paths file):
```bash
python3 tests/run.py --autonomous --save-paths
```

### ⚙️ Advanced Options
Save video during play:
```bash
python3 tests/run.py --manual --save-video
```

Set custom play duration (in seconds):
```bash
python3 tests/run.py --manual --play-seconds 60
```

Combined example - autonomous play with model, custom duration, video recording, and path management:
```bash
python3 tests/run.py --autonomous --with-model --play-seconds 120 --save-video --load-paths --save-paths --paths-file my_paths.json
```

