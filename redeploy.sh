#!/bin/sh
rm -rf build dist
python3 -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip
.build-venv/bin/python -m pip wheel --no-deps . --wheel-dir dist
APP_PATH="$HOME/Applications/Conways Game of Life.app"
"$APP_PATH/Contents/Resources/venv/bin/python" -m pip install "$PWD"/dist/conways_game_of_life-*.whl --force-reinstall
rm -rf .build-venv