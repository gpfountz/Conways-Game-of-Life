# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Exercise deployment selection, replacement, and recovery in disposable folders."""

from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

import pytest

from scripts import deploy


def existing_bundle(path: Path, identifier: str = deploy.BUNDLE_ID) -> None:
    """Create recognizable bundle metadata and a marker for the old installation."""
    contents: Path = path / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_bytes(
        plistlib.dumps({"CFBundleIdentifier": identifier})
    )
    (path / "old.txt").write_text("previous installation")


def test_detect_install_and_update(tmp_path: Path) -> None:
    """The same destination selects installation first and update once it exists."""
    bundle: Path = tmp_path / "Conways Game of Life.app"
    assert deploy.deployment_action(bundle) == "Install"
    existing_bundle(bundle)
    assert deploy.deployment_action(bundle) == "Update"


@pytest.mark.parametrize("kind", ["other-app", "directory", "symlink"])
def test_unrelated_destinations_are_rejected(tmp_path: Path, kind: str) -> None:
    """An unrelated directory, other application, or symlink must never be replaced."""
    bundle: Path = tmp_path / "Conways Game of Life.app"
    if kind == "other-app":
        existing_bundle(bundle, "org.example.other")
    elif kind == "directory":
        bundle.mkdir()
    else:
        bundle.symlink_to(tmp_path / "absent.app")
    with pytest.raises(ValueError):
        deploy.deployment_action(bundle)


@pytest.mark.parametrize("update", [False, True])
def test_promote_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, update: bool
) -> None:
    """A successful install or update verifies the final path and removes its backup."""
    destination: Path = tmp_path / "Conways Game of Life.app"
    staged: Path = tmp_path / "staged.app"
    staged.mkdir()
    (staged / "new.txt").write_text("new installation")
    if update:
        existing_bundle(destination)
    verified: list[Path] = []

    def verify(bundle: Path, version: str) -> None:
        """Record verification after the staged installation has moved."""
        assert version == "1.2.3"
        assert (bundle / "new.txt").exists()
        verified.append(bundle)

    monkeypatch.setattr(deploy, "verify_bundle", verify)
    deploy.replace_bundle(staged, destination, "1.2.3")
    assert verified == [destination]
    assert not (destination / "old.txt").exists()
    assert not list(tmp_path.glob(".*.backup-*"))


@pytest.mark.parametrize("update", [False, True])
def test_failed_verification_rolls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, update: bool
) -> None:
    """A failed final-path check restores an old installation or removes a new one."""
    destination: Path = tmp_path / "Conways Game of Life.app"
    staged: Path = tmp_path / "staged.app"
    staged.mkdir()
    if update:
        existing_bundle(destination)

    def fail_verification(bundle: Path, version: str) -> None:
        """Simulate a runtime that breaks after relocation."""
        raise subprocess.CalledProcessError(1, "smoke-test")

    monkeypatch.setattr(deploy, "verify_bundle", fail_verification)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.replace_bundle(staged, destination, "1.2.3")
    assert destination.exists() == update
    if update:
        assert (destination / "old.txt").read_text() == "previous installation"


def test_build_failure_preserves_installed_application(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Dependency or build failures leave the installed app intact and remove staging."""
    destination: Path = tmp_path / "Conways Game of Life.app"
    existing_bundle(destination)

    def ignore_stopped(bundle: Path) -> None:
        """Avoid reading the host process list during this isolated failure test."""

    def fail_build(workspace: Path) -> Path:
        """Simulate a failed wheel build before any installation changes."""
        raise subprocess.CalledProcessError(1, "pip wheel")

    monkeypatch.setattr(deploy, "ensure_stopped", ignore_stopped)
    monkeypatch.setattr(deploy, "build_wheel", fail_build)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.deploy(destination, "1.2.3")
    assert (destination / "old.txt").read_text() == "previous installation"
    assert not list(tmp_path.glob(".conways-deploy-*"))


def test_running_application_blocks_update(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An app using the installed runtime must be closed before it can be replaced."""
    bundle: Path = tmp_path / "Conways Game of Life.app"

    def processes(arguments: list[str], *, text: bool) -> str:
        """Return a representative application command with spaces in its path."""
        return f"{bundle}/Contents/Resources/venv/bin/python -I -m gameoflife.main\n"

    monkeypatch.setattr(subprocess, "check_output", processes)
    with pytest.raises(ValueError, match="Quit Conway"):
        deploy.ensure_stopped(bundle)


def test_dry_run_has_no_side_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Previewing an installation must neither create its parent nor invoke a build."""
    bundle: Path = tmp_path / "absent" / "Conways Game of Life.app"
    monkeypatch.setattr(deploy, "validate_host", lambda: None)
    monkeypatch.setattr(
        "sys.argv", ["deploy.py", "--dry-run", "--app-path", str(bundle)]
    )
    assert deploy.main() == 0
    assert "Install Conway" in capsys.readouterr().out
    assert not bundle.parent.exists()
