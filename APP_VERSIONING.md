<!-- SPDX-FileCopyrightText: 2026 Greg Pfountz -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Automatic application versions

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
