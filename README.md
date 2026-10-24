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

## Automatic application versions

`src/gameoflife/__init__.py` is the authoritative application version. Setuptools,
the About dialog, and the bundle metadata writer consume it. The build date and
any existing `CFBundleVersion` are independent and are preserved.

Install the Git integration once per clone using Python 3.10 or later:

```zsh
.venv/bin/python scripts/app_versioning.py install
```

This repository publishes `master` to `origin/master`. Installation is repeatable,
respects `core.hooksPath`, and refuses to overwrite unrelated hooks or merge
drivers. Reinstall after moving the checkout or replacing its Python environment;
resolve any reported driver path mismatch explicitly in local Git configuration.
Worktrees use their own working directory and the shared Git configuration/hooks.
An existing hook requires deliberate integration before installation can proceed.

The first nonempty commit after a successfully published batch increments patch
once; further commits before publication keep that version. Hooks query the
actual designated remote branch and check ancestry. A failed push, tags-only push,
or push of another branch leaves the batch open. Unknown and bug-fix branches use
patch batches. No hook pushes anything. Missing remote access, missing fetched
objects, nonstandard ref mappings, and divergent publication history stop with
recovery instructions rather than guessing. Fetch and merge/rebase as appropriate,
then retry. The installer requires a standard fetch mapping and a known remote;
a first commit in an unborn repository retains its existing initial version.

Declare a genuine new feature before its first commit:

```zsh
git switch -c codex/my-feature
.venv/bin/python scripts/app_versioning.py classify feature
```

A feature receives one minor increment, resetting patch. After its first push,
follow-up commits and PR repairs use patch batches. Names do not imply feature
intent. Explicit fix classification always wins:

```zsh
.venv/bin/python scripts/app_versioning.py classify fix
```

Feature identity is recorded in commit trailers, so a clone, rename, or recreation
of an existing feature does not allocate another minor. To start a separate feature
from history that still carries another feature's identity, create a new branch
from `master` and use `classify feature --new-feature`. To correct a classification
before its first successful commit, run `classify` again. After allocation, retain
the allocated version and use fix batches; do not rewrite published history.
If a failed commit already staged a prepared version, restore only its numeric
version field to HEAD's value before changing classification.

Compatible merges keep the higher version without an extra bump. The merge driver
preserves non-version edits and leaves real content conflicts for resolution.
Fast-forward merges carry the incoming version. Unpublished amendments and rebase
replays preserve existing allocations. Amending published commits and rewriting
published history are unsupported; use a follow-up commit. Rebase of unpublished
work is supported; after replay, publication ancestry must still be compatible.

Only an explicit user request authorizes a major change. Stage the new shared
version and use the override for that single commit:

```zsh
APP_VERSION_ALLOW_MAJOR=1 git commit -m "Begin explicitly authorized major release"
```

Other staged manual version changes are rejected. Cross-major merges require
explicit authorization: stage the chosen higher version and use that same override.
Empty commits do not advance the version. Failed attempts are retryable without
another increment. Hooks retain
unrelated staged/unstaged changes and honor selected-file commits and
`GIT_INDEX_FILE`; a separately unstaged edit to the version field must be resolved
before preparation. The workflow adds `App-Version-*` trailers to successful
nonempty commits for durable branch/allocation identification.

Hooks are clone-local and can be bypassed (`--no-verify` skips the preparation and
commit-message hooks). Web edits, other unconfigured clones, CI-generated
commits, cherry-pick/sequencer workflows, and deliberately bypassed hooks are not
covered. Reinstall in each clone. This policy identifies release batches; concurrent
branches can share a version, and versions are not unique build identifiers.

Behavioral tests use disposable repositories and a local bare remote:

```zsh
.venv/bin/python -m pytest -q tests/test_app_versioning.py
```
