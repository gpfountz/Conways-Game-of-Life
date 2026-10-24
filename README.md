<!-- SPDX-FileCopyrightText: 2026 Greg Pfountz -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

![Conway's Game of Life](src/gameoflife/assets/conways-life-icon.png)

# Conway's Game of Life

A native-feeling macOS desktop implementation of Conway's Game of Life, built with PySide6.

## License

Copyright (C) 2026 Greg Pfountz. The original project source is licensed under
[GNU GPL version 3 only](LICENSE) (`GPL-3.0-only`), with no warranty to the extent
permitted by law. You may modify and redistribute it under those terms.
See [licensing and contributions](LICENSING.md) for reuse guidance, material
exceptions, and binary distribution status, and the
[third-party notices](src/gameoflife/legal_texts/THIRD_PARTY_NOTICES.md) for separate
dependency terms. The app's **About Conway's Game of Life** dialog provides offline legal texts.

## Development Run

Requires Python 3.10 or later. From the project checkout, create a local
virtual environment and install the dependencies:

```zsh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

After the initial setup, launch app with:

```zsh
.venv/bin/conways-game-of-life
```

run all tests with:

```zsh
.venv/bin/python -m pytest -q
```

Check required legal resources and preserved upstream notices with:

```zsh
.venv/bin/python scripts/check_legal_resources.py
```

run one test with:

```zsh
.venv/bin/python -m pytest -q tests/test_life.py::test_blinker_oscillates
```

run ruff python linter tests with:

```zsh
.venv/bin/python -m ruff check src tests; .venv/bin/python -m mypy --strict src tests
```

## Deployment

These instructions build a wheel, install it into an isolated virtual
environment inside a regular macOS application bundle, and install that bundle
in `~/Applications`. The application will then appear in Finder, Launchpad,
and Spotlight like any other macOS application.

Requires Python 3.10 or later. From the project checkout, run:

```zsh
# 1. Build a wheel from this checkout.
rm -rf build dist src/conways_game_of_life.egg-info
python3 -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip
.build-venv/bin/python -m pip wheel --no-deps . --wheel-dir dist

# 2. Create the application bundle and its dedicated virtual environment.
APP_PATH="$HOME/Applications/Conways Game of Life.app"
mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources"
python3 -m venv "$APP_PATH/Contents/Resources/venv"

# 3. Install the freshly built wheel into that virtual environment.
"$APP_PATH/Contents/Resources/venv/bin/python" -m pip install \
  "$PWD"/dist/conways_game_of_life-*.whl

# 4. Add the macOS application metadata and launcher.
cp "$APP_PATH/Contents/Resources/venv/share/conways-game-of-life/ConwaysGameOfLife.icns" \
  "$APP_PATH/Contents/Resources/ConwaysGameOfLife.icns"

.build-venv/bin/python scripts/bundle_metadata.py "$APP_PATH"

cat > "$APP_PATH/Contents/MacOS/conways-game-of-life" <<'LAUNCHER'
#!/bin/zsh
set -euo pipefail
APP_ROOT="${0:A:h:h}"
exec "$APP_ROOT/Resources/venv/bin/conways-game-of-life"
LAUNCHER
chmod +x "$APP_PATH/Contents/MacOS/conways-game-of-life"

# 5. Confirm that macOS recognizes the bundle, then launch it.
plutil -lint "$APP_PATH/Contents/Info.plist"
open "$APP_PATH"
```

To update the application later, rebuild the wheel (step 1), then repeat step
3 and refresh its metadata with `scripts/bundle_metadata.py` (step 4). The existing
application bundle and its virtual environment can stay in place.

## Controls

- Click or left-drag across cells to toggle them alive or dead; a cell toggles only once per stroke.
- Right-click or middle-drag to pan the infinite grid.
- Scroll to zoom in and out.
- Arrow keys pan the grid four cells at a time.
- `Space`: run or pause.
- `S`: advance one generation.
- `N`: new randomized universe.
- `C`: clear the grid.
- `=` / `-`: zoom in / out.
- `0`: center the pattern.
- '1', '2', '3': slow, medium, fast speed

Use **Patterns** for classic built-in configurations including still lifes, oscillators, a glider, and Gosper's glider gun.

## Rules

The game follows Conway's B3/S23 rule: live cells survive with two or three live neighbors; dead cells are born with exactly three live neighbors. Updates are simultaneous and the universe is represented as an unbounded sparse set of live cells.
