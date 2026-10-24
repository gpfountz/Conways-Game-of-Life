# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Exercise installed version hooks using disposable repositories and bare remotes."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY: Path = Path(__file__).resolve().parents[1]
SOURCE: str = "src/gameoflife/__init__.py"
SCRIPT: str = "scripts/app_versioning.py"


class Sandbox:
    """A real Git checkout with no connection to the user's hosted repository."""

    def __init__(self, parent: Path) -> None:
        """Seed a published primary branch and install the actual workflow."""
        self.path: Path = parent / "checkout with spaces"
        self.remote: Path = parent / "remote.git"
        self.sequence: int = 0
        self.environment: dict[str, str] = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.environment.update(
            {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        )
        self.path.mkdir()
        self.run("init", "--bare", str(self.remote))
        self.run("init", "-b", "master")
        self.run("config", "user.name", "Version Test")
        self.run("config", "user.email", "version@example.invalid")
        self.run("config", "commit.gpgSign", "false")
        self.run("config", "core.autocrlf", "false")
        (self.path / SOURCE).parent.mkdir(parents=True)
        (self.path / SOURCE).write_text('__version__: str = "1.0.0"\n')
        (self.path / "scripts").mkdir()
        shutil.copy2(REPOSITORY / SCRIPT, self.path / SCRIPT)
        shutil.copy2(REPOSITORY / ".gitattributes", self.path / ".gitattributes")
        self.run("add", ".")
        self.run("commit", "-m", "seed")
        self.run("remote", "add", "origin", str(self.remote))
        self.run("push", "-u", "origin", "master")
        self.tool("install")

    def process(
        self,
        command: list[str],
        *,
        check: bool = True,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command with isolated Git settings and inspect failures."""
        result: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            cwd=self.path,
            env=self.environment | (environment or {}),
            capture_output=True,
            text=True,
            check=False,
        )
        if check:
            assert result.returncode == 0, result.stdout + result.stderr
        return result

    def run(
        self,
        *arguments: str,
        check: bool = True,
        environment: dict[str, str] | None = None,
    ) -> str:
        """Run Git inside the disposable checkout."""
        return self.process(
            ["git", *arguments], check=check, environment=environment
        ).stdout.strip()

    def tool(
        self, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run the same CLI used by the actual repository hooks."""
        return self.process([sys.executable, SCRIPT, *arguments], check=check)

    def change(self, filename: str = "work.txt") -> str:
        """Create a real staged edit, commit through hooks, and return its version."""
        self.sequence += 1
        (self.path / filename).write_text(f"change {self.sequence}\n")
        self.run("add", filename)
        self.run("commit", "-m", f"change {self.sequence}")
        return self.version()

    def version(self, revision: str = "HEAD") -> str:
        """Read the exact committed version without importing application dependencies."""
        return self.run("show", f"{revision}:{SOURCE}").split('"')[1]


@pytest.fixture
def repository(tmp_path: Path) -> Sandbox:
    """Provide an isolated installed checkout for each behavior test."""
    return Sandbox(tmp_path)


def test_patch_batches_require_successful_designated_push(repository: Sandbox) -> None:
    """Close only published batches, ignoring tags, other branches, and rejected pushes."""
    assert repository.change() == "1.0.1"
    assert repository.change() == "1.0.1"
    repository.run("tag", "test-tag")
    repository.run("push", "origin", "test-tag")
    repository.run("push", "origin", "HEAD:refs/heads/another")
    assert repository.change() == "1.0.1"
    reject: Path = repository.remote / "hooks/pre-receive"
    reject.write_text("#!/bin/sh\nexit 1\n")
    reject.chmod(0o755)
    result: subprocess.CompletedProcess[str] = repository.process(
        ["git", "push", "origin", "master"], check=False
    )
    assert result.returncode != 0
    assert repository.change() == "1.0.1"
    reject.unlink()
    repository.run("push", "origin", "master")
    assert repository.change() == "1.0.2"
    assert repository.change() == "1.0.2"


def test_feature_minor_once_then_pr_patch_batches(repository: Sandbox) -> None:
    """A feature gets one minor allocation and subsequent fix batches get patches."""
    repository.change()
    repository.run("push", "origin", "master")
    repository.change()
    repository.run("push", "origin", "master")
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    assert repository.version() == "1.0.2"
    assert repository.change() == "1.1.0"
    assert repository.change() == "1.1.0"
    repository.run("push", "-u", "origin", "codex/feature")
    assert repository.change() == "1.1.1"
    assert repository.change() == "1.1.1"
    repository.run("push", "origin", "codex/feature")
    assert repository.change() == "1.1.2"


@pytest.mark.parametrize("explicit", [False, True])
def test_unknown_and_explicit_fix_branches_use_patch(
    repository: Sandbox, explicit: bool
) -> None:
    """A feature-like name never overrides explicit fix or unknown branch intent."""
    repository.run("switch", "-c", "feature/named-like-a-feature")
    if explicit:
        repository.tool("classify", "fix")
    assert repository.change() == "1.0.1"
    assert repository.change() == "1.0.1"


@pytest.mark.parametrize("fast_forward", [False, True])
def test_merges_preserve_incoming_version(
    repository: Sandbox, fast_forward: bool
) -> None:
    """Both automatic merge commits and fast-forward merges retain feature versions."""
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    repository.change("feature.txt")
    repository.run("push", "origin", "codex/feature")
    repository.run("switch", "master")
    if not fast_forward:
        repository.change("primary.txt")
    repository.run(
        "merge",
        "--ff-only" if fast_forward else "--no-ff",
        "codex/feature",
        "-m",
        "merge feature",
    )
    assert repository.version() == "1.1.0"
    assert repository.change("next.txt") == "1.1.0"
    repository.run("push", "origin", "master")
    assert repository.change("next.txt") == "1.1.1"


def test_merge_keeps_newer_primary_and_nonversion_edits(repository: Sandbox) -> None:
    """A lower incoming version cannot downgrade primary or erase source-file edits."""
    repository.run("switch", "-c", "codex/older")
    with (repository.path / SOURCE).open("a") as stream:
        stream.write("\nOLDER_VALUE: int = 7\n")
    repository.run("add", SOURCE)
    repository.change("older.txt")
    repository.run("switch", "master")
    repository.change("primary.txt")
    repository.run("push", "origin", "master")
    repository.change("primary.txt")
    repository.run("merge", "--no-ff", "codex/older", "-m", "merge older")
    assert repository.version() == "1.0.2"
    assert "OLDER_VALUE: int = 7" in repository.run("show", f"HEAD:{SOURCE}")


def test_unpublished_amend_and_rebase_do_not_reallocate(repository: Sandbox) -> None:
    """Amend and Git rebase replay retain an allocated feature minor."""
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    assert repository.change("feature.txt") == "1.1.0"
    repository.run("commit", "--amend", "-m", "amended feature")
    assert repository.version() == "1.1.0"
    repository.change("second.txt")
    repository.run("switch", "master")
    repository.change("primary.txt")
    repository.run("switch", "codex/feature")
    repository.run("rebase", "master")
    assert repository.version() == "1.1.0"
    assert repository.change("third.txt") == "1.1.0"


def test_empty_commits_and_failed_hook_retry(repository: Sandbox) -> None:
    """No payload means no bump, and retry after a later hook failure is idempotent."""
    assert (
        repository.process(["git", "commit", "-m", "empty"], check=False).returncode
        != 0
    )
    repository.run("commit", "--allow-empty", "-m", "allowed empty")
    assert repository.version() == "1.0.0"
    reject: Path = repository.path / ".git/hooks/commit-msg"
    original_hook: str = reject.read_text()
    reject.write_text("#!/bin/sh\nexit 1\n")
    reject.chmod(0o755)
    (repository.path / "work.txt").write_text("payload\n")
    repository.run("add", "work.txt")
    assert (
        repository.process(["git", "commit", "-m", "fails"], check=False).returncode
        != 0
    )
    assert '"1.0.1"' in repository.run("show", f":{SOURCE}")
    reject.write_text(original_hook)
    repository.run("commit", "-m", "retry")
    assert repository.version() == "1.0.1"


def test_partial_staging_and_version_comments_are_preserved(
    repository: Sandbox,
) -> None:
    """Only the numeric field is added to a partially staged version source."""
    path: Path = repository.path / SOURCE
    path.write_text(path.read_text() + "\nSTAGED_VALUE: int = 1\n")
    repository.run("add", SOURCE)
    path.write_text(path.read_text() + "UNSTAGED_VALUE: int = 2\n\n")
    repository.run("commit", "-m", "partial source")
    committed: str = repository.run("show", f"HEAD:{SOURCE}")
    assert '"1.0.1"' in committed and "STAGED_VALUE" in committed
    assert "UNSTAGED_VALUE" not in committed
    assert "UNSTAGED_VALUE" in path.read_text() and path.read_text().endswith("\n\n")
    assert not repository.run("diff", "--cached")


def test_alternate_index_and_selected_file_commits(
    repository: Sandbox, tmp_path: Path
) -> None:
    """Hooks respect temporary indexes and avoid adding other staged files to commits."""
    (repository.path / "unrelated.txt").write_text("keep staged\n")
    repository.run("add", "unrelated.txt")
    (repository.path / "selected.txt").write_text("selected\n")
    repository.run("add", "selected.txt")
    repository.run("commit", "-m", "selected only", "--", "selected.txt")
    assert repository.version() == "1.0.1"
    assert repository.run("diff", "--cached", "--name-only") == "unrelated.txt"
    alternate: dict[str, str] = {"GIT_INDEX_FILE": str(tmp_path / "alternate-index")}
    repository.run("read-tree", "HEAD", environment=alternate)
    (repository.path / "alternate.txt").write_text("alternate\n")
    repository.run("add", "alternate.txt", environment=alternate)
    repository.run("commit", "-m", "alternate index", environment=alternate)
    assert repository.version() == "1.0.1"
    assert "unrelated.txt" not in repository.run("ls-tree", "--name-only", "HEAD")


def test_separate_unstaged_version_change_stops_safely(repository: Sandbox) -> None:
    """An unstaged manual version cannot be silently overwritten or staged."""
    path: Path = repository.path / SOURCE
    path.write_text(path.read_text().replace("1.0.0", "1.8.0"))
    (repository.path / "payload.txt").write_text("payload\n")
    repository.run("add", "payload.txt")
    result: subprocess.CompletedProcess[str] = repository.process(
        ["git", "commit", "-m", "unsafe version"], check=False
    )
    assert result.returncode != 0 and "unstaged edit" in result.stderr
    assert "1.8.0" in path.read_text()
    assert repository.run("diff", "--cached", "--name-only") == "payload.txt"


def test_real_nonversion_merge_conflicts_remain(repository: Sandbox) -> None:
    """Conflicting non-version content must not disappear in version reconciliation."""
    path: Path = repository.path / SOURCE
    path.write_text(path.read_text() + "LABEL: str = 'base'\n")
    repository.run("add", SOURCE)
    repository.run("commit", "-m", "add label")
    repository.run("push", "origin", "master")
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    path.write_text(path.read_text().replace("'base'", "'theirs'"))
    repository.run("add", SOURCE)
    repository.run("commit", "-m", "theirs")
    repository.run("switch", "master")
    path.write_text(path.read_text().replace("'base'", "'ours'"))
    repository.run("add", SOURCE)
    repository.run("commit", "-m", "ours")
    assert (
        repository.process(["git", "merge", "codex/feature"], check=False).returncode
        != 0
    )
    assert "<<<<<<<" in path.read_text()
    assert "'ours'" in path.read_text() and "'theirs'" in path.read_text()


def test_major_override_is_explicit_and_one_commit(repository: Sandbox) -> None:
    """Reject accidental majors and restore normal patch behavior after an override."""
    path: Path = repository.path / SOURCE
    path.write_text(path.read_text().replace("1.0.0", "2.0.0"))
    repository.run("add", SOURCE)
    assert (
        repository.process(
            ["git", "commit", "-m", "accidental major"], check=False
        ).returncode
        != 0
    )
    repository.run(
        "commit", "-m", "authorized major", environment={"APP_VERSION_ALLOW_MAJOR": "1"}
    )
    assert repository.version() == "2.0.0"
    assert repository.change() == "2.0.0"
    repository.run("push", "origin", "master")
    assert repository.change() == "2.0.1"


def test_install_is_repeatable_and_refuses_conflicting_hooks(
    repository: Sandbox,
) -> None:
    """Installation changes only owned hooks and supports configured hook directories."""
    repository.tool("install")
    repository.tool("install")
    repository.run("config", "core.hooksPath", ".custom-hooks")
    repository.tool("install")
    assert repository.change() == "1.0.1"
    target: Path = repository.path / ".custom-hooks/pre-commit"
    target.write_text("#!/bin/sh\necho unrelated hook\n")
    assert repository.tool("install", check=False).returncode != 0
    assert "unrelated hook" in target.read_text()
    repository.run("config", "merge.app-version.driver", "other-driver")
    assert repository.tool("install", check=False).returncode != 0


def test_feature_rename_and_new_clone_recover_identity(
    repository: Sandbox, tmp_path: Path
) -> None:
    """Durable feature trailers survive rename, fresh clone, and recreated branches."""
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    repository.change()
    repository.run("branch", "-m", "codex/renamed")
    assert repository.change() == "1.1.0"
    repository.run("push", "origin", "codex/renamed")
    clone: Path = tmp_path / "fresh clone"
    repository.run(
        "clone", "--branch", "codex/renamed", str(repository.remote), str(clone)
    )
    repository.path = clone
    repository.run("config", "user.name", "Version Test")
    repository.run("config", "user.email", "version@example.invalid")
    repository.tool("install")
    repository.tool("classify", "feature")
    assert repository.change() == "1.1.1"
    repository.run("switch", "-c", "codex/recreated")
    repository.tool("classify", "feature")
    assert repository.change() == "1.1.1"


def test_stale_refs_missing_remote_and_divergence_fail_safely(
    repository: Sandbox,
) -> None:
    """Stale tracking refs do not pretend a push failed or conceal incompatible history."""
    repository.change()
    old: str = repository.run("rev-parse", "origin/master")
    repository.run("push", "origin", "master")
    repository.run("update-ref", "refs/remotes/origin/master", old)
    assert repository.change() == "1.0.2"
    repository.run("config", "branch.master.merge", "refs/tags/wrong")
    (repository.path / "blocked.txt").write_text("blocked\n")
    repository.run("add", "blocked.txt")
    assert repository.tool("prepare", check=False).returncode != 0
    repository.run("config", "branch.master.merge", "refs/heads/master")
    repository.run("config", "remote.origin.url", str(repository.remote / "missing"))
    (repository.path / "blocked.txt").write_text("blocked\n")
    repository.run("add", "blocked.txt")
    assert repository.tool("prepare", check=False).returncode != 0
    repository.run("config", "remote.origin.url", str(repository.remote))
    repository.run("config", "appVersion.remote", "missing-remote")
    assert repository.tool("prepare", check=False).returncode != 0


def test_install_and_commit_in_linked_worktree(
    repository: Sandbox, tmp_path: Path
) -> None:
    """Linked worktrees resolve hooks, configuration, and the active source correctly."""
    worktree: Path = tmp_path / "linked worktree"
    repository.run("worktree", "add", "-b", "codex/worktree", str(worktree))
    repository.path = worktree
    repository.tool("install")
    assert repository.change() == "1.0.1"


def test_bundle_metadata_preserves_internal_build(tmp_path: Path) -> None:
    """The bundle version follows the Python source while the platform build stays fixed."""
    bundle: Path = tmp_path / "Life.app"
    metadata_path: Path = bundle / "Contents/Info.plist"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_bytes(
        plistlib.dumps({"CFBundleVersion": "812", "CustomKey": "keep"})
    )
    subprocess.run(
        [sys.executable, str(REPOSITORY / "scripts/bundle_metadata.py"), str(bundle)],
        check=True,
    )
    metadata: dict[str, str] = plistlib.loads(metadata_path.read_bytes())
    from gameoflife import __version__

    assert metadata["CFBundleShortVersionString"] == __version__
    assert metadata["CFBundleVersion"] == "812" and metadata["CustomKey"] == "keep"


def test_remote_advance_and_divergence_require_reconciliation(
    repository: Sandbox,
) -> None:
    """Fetching another author's history is never evidence of local publication."""
    repository.run("switch", "-c", "other-author")
    repository.change("other.txt")
    other: str = repository.run("rev-parse", "HEAD")
    repository.run("push", "origin", f"{other}:refs/heads/master")
    repository.run("switch", "master")
    (repository.path / "payload.txt").write_text("payload\n")
    repository.run("add", "payload.txt")
    result: subprocess.CompletedProcess[str] = repository.tool("prepare", check=False)
    assert result.returncode != 0 and "ahead or divergent" in result.stderr
    repository.run("merge", "--ff-only", "other-author")
    assert repository.change("payload.txt") == "1.0.2"
    repository.run("switch", "other-author")
    repository.change("other.txt")
    other = repository.run("rev-parse", "HEAD")
    repository.run("push", "origin", f"{other}:refs/heads/master")
    repository.run("switch", "master")
    repository.run("fetch", "origin")
    (repository.path / "payload.txt").write_text("divergent\n")
    repository.run("add", "payload.txt")
    result = repository.tool("prepare", check=False)
    assert result.returncode != 0 and "ahead or divergent" in result.stderr


def test_feature_retry_and_corrected_classification(repository: Sandbox) -> None:
    """Empty/aborted commits do not consume feature allocation or lock in mistaken intent."""
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    repository.run("commit", "--allow-empty", "-m", "empty feature")
    assert repository.version() == "1.0.0"
    rejection: Path = repository.path / ".git/hooks/commit-msg"
    original_hook: str = rejection.read_text()
    rejection.write_text("#!/bin/sh\nexit 1\n")
    rejection.chmod(0o755)
    (repository.path / "payload.txt").write_text("payload\n")
    repository.run("add", "payload.txt")
    assert (
        repository.process(
            ["git", "commit", "-m", "feature attempt"], check=False
        ).returncode
        != 0
    )
    assert '"1.1.0"' in repository.run("show", f":{SOURCE}")
    rejection.write_text(original_hook)
    repository.run("commit", "-m", "successful feature")
    assert repository.version() == "1.1.0"
    repository.tool("classify", "fix")
    repository.tool("classify", "feature")
    assert repository.change() == "1.1.0"


def test_cross_major_merge_requires_explicit_resolution(repository: Sandbox) -> None:
    """Cross-major merges stop before automatically selecting either major."""
    repository.run("switch", "-c", "codex/major")
    path: Path = repository.path / SOURCE
    path.write_text(path.read_text().replace("1.0.0", "2.0.0"))
    repository.run("add", SOURCE)
    repository.run(
        "commit", "-m", "authorized major", environment={"APP_VERSION_ALLOW_MAJOR": "1"}
    )
    repository.run("switch", "master")
    repository.change("primary.txt")
    result: subprocess.CompletedProcess[str] = repository.process(
        ["git", "merge", "--no-ff", "codex/major", "-m", "merge major"], check=False
    )
    assert result.returncode != 0
    assert repository.version() == "1.0.1"
    path.write_text('__version__: str = "2.0.0"\n')
    repository.run("add", SOURCE)
    repository.run(
        "commit",
        "-m",
        "explicitly resolved major merge",
        environment={"APP_VERSION_ALLOW_MAJOR": "1"},
    )
    assert repository.version() == "2.0.0"


def test_missing_published_objects_fail_before_preparation(
    repository: Sandbox, tmp_path: Path
) -> None:
    """Remote changes absent from local storage require an explicit fetch."""
    clone: Path = tmp_path / "other clone"
    repository.run("clone", str(repository.remote), str(clone))
    original: Path = repository.path
    repository.path = clone
    repository.run("switch", "master")
    repository.run("config", "user.name", "Other")
    repository.run("config", "user.email", "other@example.invalid")
    (clone / "other.txt").write_text("remote change\n")
    repository.run("add", "other.txt")
    repository.run("commit", "-m", "other clone change")
    repository.run("push", "origin", "master")
    repository.path = original
    (original / "payload.txt").write_text("payload\n")
    repository.run("add", "payload.txt")
    result: subprocess.CompletedProcess[str] = repository.tool("prepare", check=False)
    assert result.returncode != 0 and "missing locally" in result.stderr


def test_cancelled_editor_and_empty_message_leave_retryable_version(
    repository: Sandbox,
) -> None:
    """Metadata trailers must never turn an empty or aborted message into a commit."""
    repository.run("switch", "-c", "codex/feature")
    repository.tool("classify", "feature")
    (repository.path / "payload.txt").write_text("payload\n")
    repository.run("add", "payload.txt")
    original: str = repository.run("rev-parse", "HEAD")
    assert repository.process(["git", "commit", "-m", ""], check=False).returncode != 0
    assert (
        repository.process(
            ["git", "commit"], check=False, environment={"GIT_EDITOR": "false"}
        ).returncode
        != 0
    )
    assert repository.run("rev-parse", "HEAD") == original
    repository.run("commit", "-m", "successful retry")
    assert repository.version() == "1.1.0"
