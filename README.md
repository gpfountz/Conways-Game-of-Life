![Conway's Game of Life](assets/conways-life-icon.png)

# Conway's Game of Life

A native-feeling macOS desktop implementation of Conway's Game of Life, built with PySide6.

## Deployment

These instructions build a wheel, install it into an isolated virtual
environment inside a regular macOS application bundle, and install that bundle
in `~/Applications`. The application will then appear in Finder, Launchpad,
and Spotlight like any other macOS application.

Requires Python 3.10 or later. From the project checkout, run:

```zsh
# 1. Build a wheel from this checkout.
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

cat > "$APP_PATH/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDisplayName</key>
  <string>Conway's Game of Life</string>
  <key>CFBundleExecutable</key>
  <string>conways-game-of-life</string>
  <key>CFBundleIdentifier</key>
  <string>com.greg.conwaysgameoflife</string>
  <key>CFBundleIconFile</key>
  <string>ConwaysGameOfLife</string>
  <key>CFBundleName</key>
  <string>Conway's Game of Life</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0.8</string>
</dict>
</plist>
PLIST

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
3. The existing application bundle and its virtual environment can stay in
place.

## Controls

- Click a cell to toggle it alive or dead.
- Drag on the trackpad (or right-click/middle-drag) to pan the infinite grid.
- Scroll to zoom in and out.
- Arrow keys pan the grid four cells at a time.
- `Space`: run or pause.
- **Game > Step Forward**: advance one generation.
- `Command-N`: new randomized universe.
- **Game > Clear**: clear the grid.
- `Command-+` / `Command--`: zoom in / out.
- `Command-0`: center the pattern.

Use **Patterns** for classic built-in configurations including still lifes, oscillators, a glider, and Gosper's glider gun.

## Rules

The game follows Conway's B3/S23 rule: live cells survive with two or three live neighbors; dead cells are born with exactly three live neighbors. Updates are simultaneous and the universe is represented as an unbounded sparse set of live cells.
