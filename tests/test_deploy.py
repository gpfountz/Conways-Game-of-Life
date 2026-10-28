# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Exercise deployment selection, replacement, and recovery in disposable folders."""

from __future__ import annotations

import plistlib
import subprocess
import sys
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


@pytest.mark.parametrize("failure", ["build", "prepare", "verify"])
def test_staging_failure_preserves_installed_application(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    """Build, runtime install, and staged-check failures preserve the installed app."""
    destination: Path = tmp_path / "Conways Game of Life.app"
    existing_bundle(destination)

    def ignore_stopped(bundle: Path) -> None:
        """Avoid reading the host process list during this isolated failure test."""

    def build(workspace: Path, python: Path) -> Path:
        """Simulate a wheel build that can fail before runtime installation."""
        if failure == "build":
            raise subprocess.CalledProcessError(1, "pip wheel")
        return workspace / "application.whl"

    def prepare(bundle: Path, wheel: Path, previous: Path, python: Path) -> None:
        """Simulate a fresh bundle environment whose dependency install can fail."""
        bundle.mkdir()
        if failure == "prepare":
            raise subprocess.CalledProcessError(1, "pip install")

    def verify(bundle: Path, version: str) -> None:
        """Simulate a failed runtime check before any replacement."""
        raise subprocess.CalledProcessError(1, "pip check")

    monkeypatch.setattr(deploy, "ensure_stopped", ignore_stopped)
    monkeypatch.setattr(deploy, "project_python", lambda: tmp_path / "python")
    monkeypatch.setattr(deploy, "synchronize_dependencies", lambda python: None)
    monkeypatch.setattr(deploy, "build_wheel", build)
    monkeypatch.setattr(deploy, "prepare_bundle", prepare)
    monkeypatch.setattr(deploy, "verify_bundle", verify)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.deploy(destination, "1.2.3")
    assert (destination / "old.txt").read_text() == "previous installation"
    assert not list(tmp_path.glob(".conways-deploy-*"))


def test_bundle_install_uses_project_requirements(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep requirements constraints active when installing the application wheel."""
    bundle: Path = tmp_path / "staged.app"
    python: Path = tmp_path / ".venv/bin/python"
    environment: Path = bundle / "Contents/Resources/venv"
    wheel: Path = tmp_path / "application.whl"
    commands: list[tuple[str, ...]] = []

    def command(*arguments: str, cwd: Path | None = None) -> None:
        """Record environment creation and stop at the simulated pip install."""
        commands.append(arguments)
        if "install" in arguments:
            raise subprocess.CalledProcessError(1, arguments)

    monkeypatch.setattr(deploy, "run", command)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.prepare_bundle(bundle, wheel, tmp_path / "old.app", python)
    assert commands == [
        (str(python), "-m", "venv", str(environment)),
        (
            str(environment / "bin/python"),
            "-I",
            "-m",
            "pip",
            "install",
            "--requirement",
            str(deploy.ROOT / "requirements.txt"),
            str(wheel),
        ),
    ]


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
    """Previewing must not create environments, download, build, install, or launch."""
    bundle: Path = tmp_path / "absent" / "Conways Game of Life.app"
    monkeypatch.setattr(deploy, "validate_host", lambda: None)

    def unexpected_deployment(bundle: Path, version: str) -> None:
        """Reject any mutation or dependency command during a preview."""
        pytest.fail("Dry-run attempted deployment")

    def unexpected_command(*arguments: str, cwd: Path | None = None) -> None:
        """Reject subprocesses, including launching with the open option."""
        pytest.fail(f"Dry-run ran a command: {arguments}")

    monkeypatch.setattr(deploy, "deploy", unexpected_deployment)
    monkeypatch.setattr(deploy, "run", unexpected_command)
    monkeypatch.setattr(
        "sys.argv", ["deploy.py", "--dry-run", "--open", "--app-path", str(bundle)]
    )
    assert deploy.main() == 0
    assert "Install Conway" in capsys.readouterr().out
    assert not bundle.parent.exists()


@pytest.mark.parametrize("exists", [False, True])
def test_project_environment_is_created_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, exists: bool
) -> None:
    """Use the checkout environment and bootstrap only when it does not exist."""
    python: Path = tmp_path / ".venv/bin/python"
    commands: list[tuple[str, ...]] = []

    def create_environment(*arguments: str, cwd: Path | None = None) -> None:
        """Model venv creation without installing packages or starting an interpreter."""
        assert cwd == tmp_path
        commands.append(arguments)
        python.parent.mkdir(parents=True)
        python.touch()
        (python.parents[1] / "pyvenv.cfg").touch()

    if exists:
        python.parent.mkdir(parents=True)
        python.touch()
        (python.parents[1] / "pyvenv.cfg").touch()
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    monkeypatch.setattr(deploy, "run", create_environment)
    assert deploy.project_python() == python
    assert commands == (
        [] if exists else [(sys.executable, "-m", "venv", str(tmp_path / ".venv"))]
    )


@pytest.mark.parametrize("kind", ["incomplete", "symlink"])
def test_unsafe_project_environment_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str
) -> None:
    """Never overwrite a broken environment or follow an environment directory link."""
    environment: Path = tmp_path / ".venv"
    if kind == "symlink":
        environment.symlink_to(tmp_path / "external", target_is_directory=True)
    else:
        environment.mkdir()
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="symlink|incomplete"):
        deploy.project_python()


def test_dependencies_and_legal_checks_precede_build(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Synchronize and validate with the project Python before staging or promotion."""
    destination: Path = tmp_path / "Conways Game of Life.app"
    python: Path = tmp_path / ".venv/bin/python"
    events: list[str] = []

    def command(*arguments: str, cwd: Path | None = None) -> None:
        """Check exact pip commands, including the absence of upgrade flags."""
        assert cwd == deploy.ROOT
        if not events:
            assert arguments == (
                str(python),
                "-m",
                "pip",
                "install",
                "--requirement",
                str(deploy.ROOT / "requirements.txt"),
            )
            events.append("install")
        else:
            assert arguments == (str(python), "-m", "pip", "check")
            events.append("pip-check")

    def legal_checks() -> dict[str, bytes]:
        """Record the source integrity and legal-resource validation."""
        events.append("legal")
        return {}

    def build(workspace: Path, interpreter: Path) -> Path:
        """Record the build after asserting that it uses the project interpreter."""
        assert interpreter == python
        events.append("build")
        return workspace / "application.whl"

    def prepare(staged: Path, wheel: Path, previous: Path, interpreter: Path) -> None:
        """Model preparing a new runtime using the synchronized interpreter."""
        assert previous == destination
        assert interpreter == python
        events.append("prepare")

    def verify(staged: Path, version: str) -> None:
        """Record staged verification before promotion."""
        events.append("verify")

    def replace(staged: Path, bundle: Path, version: str) -> None:
        """Record promotion only after all prior stages succeeded."""
        events.append("replace")

    monkeypatch.setattr(deploy, "project_python", lambda: python)
    monkeypatch.setattr(deploy, "ensure_stopped", lambda bundle: None)
    monkeypatch.setattr(deploy, "run", command)
    monkeypatch.setattr(deploy, "required_files", legal_checks)
    monkeypatch.setattr(deploy, "build_wheel", build)
    monkeypatch.setattr(deploy, "prepare_bundle", prepare)
    monkeypatch.setattr(deploy, "verify_bundle", verify)
    monkeypatch.setattr(deploy, "replace_bundle", replace)
    deploy.deploy(destination, "1.2.3")
    assert events == [
        "install",
        "pip-check",
        "legal",
        "build",
        "prepare",
        "verify",
        "replace",
    ]


@pytest.mark.parametrize("update", [False, True])
@pytest.mark.parametrize("failure", ["install", "pip-check", "legal"])
def test_dependency_failure_stops_before_build_and_preserves_application(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, update: bool, failure: str
) -> None:
    """Failed installation or validation must never reach build or alter app bytes."""
    destination: Path = tmp_path / "Conways Game of Life.app"
    if update:
        existing_bundle(destination)
    before: dict[Path, bytes] = {
        path.relative_to(destination): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    }
    events: list[str] = []

    def command(*arguments: str, cwd: Path | None = None) -> None:
        """Stop at the selected dependency command without running pip."""
        stage: str = "install" if "install" in arguments else "pip-check"
        events.append(stage)
        if failure == stage:
            raise subprocess.CalledProcessError(1, arguments)

    def legal_checks() -> dict[str, bytes]:
        """Simulate a preserved upstream hash mismatch during source validation."""
        events.append("legal")
        raise ValueError("Preserved upstream notice changed")

    def unexpected_build(workspace: Path, python: Path) -> Path:
        """Fail if dependency errors are allowed to reach a build."""
        pytest.fail("Built after dependency validation failed")

    monkeypatch.setattr(deploy, "project_python", lambda: tmp_path / ".venv/bin/python")
    monkeypatch.setattr(deploy, "ensure_stopped", lambda bundle: None)
    monkeypatch.setattr(deploy, "run", command)
    monkeypatch.setattr(deploy, "required_files", legal_checks)
    monkeypatch.setattr(deploy, "build_wheel", unexpected_build)
    with pytest.raises((subprocess.CalledProcessError, ValueError)):
        deploy.deploy(destination, "1.2.3")
    assert (
        events
        == ["install", "pip-check", "legal"][
            : ["install", "pip-check", "legal"].index(failure) + 1
        ]
    )
    assert destination.exists() == update
    assert before == {
        path.relative_to(destination): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    }
    assert not list(tmp_path.glob(".conways-deploy-*"))
    assert not list(tmp_path.glob(".*.backup-*"))
