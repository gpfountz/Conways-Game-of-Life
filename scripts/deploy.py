# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Build and safely install or update the local macOS application bundle."""

from __future__ import annotations

import argparse
import fcntl
import os
import platform
import plistlib
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bundle_metadata import update_bundle
from scripts.check_legal_resources import check_wheel, required_files

BUNDLE_ID: str = "com.greg.conwaysgameoflife"
LAUNCHER: str = """#!/bin/sh
set -eu
APP_CONTENTS=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$APP_CONTENTS/Resources/venv/bin/python" -I -m gameoflife.main "$@"
"""
SMOKE_TEST: str = """
import sys
from pathlib import Path
from gameoflife import __version__, legal
from gameoflife.main import MainWindow
from Foundation import NSBundle
assert __version__ == sys.argv[1], "Installed application version differs"
assert Path(sys.prefix) == Path(sys.argv[2]), "Incorrect bundle environment"
assert legal.license_text() and legal.third_party_text()
"""


def run(*arguments: str, cwd: Path | None = None) -> None:
    """Run a build step and stop immediately if it fails."""
    subprocess.run(arguments, cwd=cwd, check=True)


def validate_host() -> None:
    """Require the Python and macOS versions supported by this checkout."""
    if sys.platform != "darwin":
        raise ValueError("Deployment requires macOS.")
    if not (3, 11) <= sys.version_info[:2] < (3, 15):
        raise ValueError("Select Python 3.11–3.14 with DEPLOY_PYTHON.")
    if int(platform.mac_ver()[0].split(".")[0]) < 13:
        raise ValueError("Deployment requires macOS 13 or later.")


def deployment_action(bundle: Path) -> str:
    """Distinguish a new install from an update without replacing unrelated files."""
    if bundle.is_symlink() or bundle.suffix != ".app":
        raise ValueError("The destination must be a regular .app bundle path.")
    if not bundle.exists():
        return "Install"
    metadata: Path = bundle / "Contents/Info.plist"
    if not metadata.is_file():
        raise ValueError(f"Destination is not an existing application bundle: {bundle}")
    if plistlib.loads(metadata.read_bytes()).get("CFBundleIdentifier") != BUNDLE_ID:
        raise ValueError(f"Destination belongs to another application: {bundle}")
    return "Update"


def ensure_stopped(bundle: Path) -> None:
    """Require the installed app to be closed before its runtime is replaced."""
    processes: str = subprocess.check_output(["/bin/ps", "-axo", "args="], text=True)
    prefix: str = str(bundle / "Contents") + "/"
    if any(line.strip().startswith(prefix) for line in processes.splitlines()):
        raise ValueError("Quit Conway's Game of Life, then run deployment again.")


def project_python() -> Path:
    """Reuse the checkout environment or create it with the selected interpreter."""
    environment: Path = ROOT / ".venv"
    python: Path = environment / "bin/python"
    if environment.is_symlink():
        raise ValueError("The project .venv must not be a symlink.")
    if not environment.exists():
        print(f"Creating project environment: {environment}", flush=True)
        run(sys.executable, "-m", "venv", str(environment), cwd=ROOT)
    if not (environment / "pyvenv.cfg").is_file() or not python.is_file():
        raise ValueError(f"Project environment is incomplete: {python}")
    return python


def synchronize_dependencies(python: Path) -> None:
    """Install declared requirements and validate dependencies and preserved notices."""
    print("Installing project dependencies from requirements.txt...", flush=True)
    run(
        str(python),
        "-m",
        "pip",
        "install",
        "--requirement",
        str(ROOT / "requirements.txt"),
        cwd=ROOT,
    )
    print("Checking installed dependency consistency...", flush=True)
    run(str(python), "-m", "pip", "check", cwd=ROOT)
    print("Checking legal resources and preserved upstream hashes...", flush=True)
    required_files()


def build_wheel(workspace: Path, python: Path) -> Path:
    """Build from a clean source copy so stale build files cannot enter the wheel."""
    source: Path = workspace / "source"
    source.mkdir()
    for name in (
        "pyproject.toml",
        "MANIFEST.in",
        "README.md",
        "LICENSE",
        "LICENSING.md",
        "APP_VERSIONING.md",
        "AGENTS.md",
        "requirements.txt",
        ".gitattributes",
    ):
        shutil.copy2(ROOT / name, source / name)
    for name in ("src", "scripts", "tests"):
        shutil.copytree(
            ROOT / name,
            source / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "*.pyc"),
        )
    output: Path = workspace / "wheels"
    run(
        str(python),
        "-m",
        "pip",
        "wheel",
        "--no-deps",
        str(source),
        "--wheel-dir",
        str(output),
        cwd=workspace,
    )
    wheels: list[Path] = list(output.glob("conways_game_of_life-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one freshly built application wheel.")
    check_wheel(wheels[0])
    return wheels[0]


def verify_bundle(bundle: Path, version: str) -> None:
    """Check installed imports, dependency consistency, legal resources, and metadata."""
    environment: Path = bundle / "Contents/Resources/venv"
    python: str = str(environment / "bin/python")
    run(python, "-I", "-m", "pip", "check", cwd=bundle)
    run(python, "-I", "-c", SMOKE_TEST, version, str(environment), cwd=bundle)
    run("/usr/bin/plutil", "-lint", str(bundle / "Contents/Info.plist"))


def prepare_bundle(bundle: Path, wheel: Path, previous: Path, python: Path) -> None:
    """Install a fresh runtime and refresh all launcher, icon, and bundle metadata."""
    resources: Path = bundle / "Contents/Resources"
    executable: Path = bundle / "Contents/MacOS/conways-game-of-life"
    executable.parent.mkdir(parents=True)
    environment: Path = resources / "venv"
    run(str(python), "-m", "venv", str(environment))
    run(
        str(environment / "bin/python"),
        "-I",
        "-m",
        "pip",
        "install",
        "--requirement",
        str(ROOT / "requirements.txt"),
        str(wheel),
    )
    shutil.copy2(
        environment / "share/conways-game-of-life/ConwaysGameOfLife.icns",
        resources / "ConwaysGameOfLife.icns",
    )
    if previous.exists():
        shutil.copy2(previous / "Contents/Info.plist", bundle / "Contents/Info.plist")
    update_bundle(bundle)
    executable.write_text(LAUNCHER, encoding="utf-8")
    executable.chmod(0o755)


def replace_bundle(staged: Path, destination: Path, version: str) -> None:
    """Promote a verified bundle and restore the previous installation on failure."""
    backup: Path = destination.with_name(f".{destination.name}.backup-{uuid4().hex}")
    had_previous: bool = destination.exists()
    if had_previous:
        destination.rename(backup)
    try:
        staged.rename(destination)
        verify_bundle(destination, version)
    except BaseException:
        if destination.exists():
            shutil.rmtree(destination)
        if had_previous:
            backup.rename(destination)
        raise
    if had_previous:
        try:
            shutil.rmtree(backup)
        except OSError:
            print(f"Update succeeded; remove the old backup manually: {backup}")


def deploy(bundle: Path, version: str) -> None:
    """Serialize deployments and stage all work beside the destination for safe renames."""
    bundle.parent.mkdir(parents=True, exist_ok=True)
    lock: Path = bundle.with_name(f".{bundle.name}.deploy.lock")
    with lock.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(
                "Another deployment to this destination is running."
            ) from error
        deployment_action(bundle)
        ensure_stopped(bundle)
        python: Path = project_python()
        synchronize_dependencies(python)
        with tempfile.TemporaryDirectory(
            prefix=".conways-deploy-", dir=bundle.parent
        ) as directory:
            workspace: Path = Path(directory)
            staged: Path = workspace / bundle.name
            print(
                "Building application wheel and checking packaged legal resources...",
                flush=True,
            )
            wheel: Path = build_wheel(workspace, python)
            print("Preparing and verifying replacement application...", flush=True)
            prepare_bundle(staged, wheel, bundle, python)
            verify_bundle(staged, version)
            ensure_stopped(bundle)
            print(
                "Installing verified application (with rollback on failure)...",
                flush=True,
            )
            replace_bundle(staged, bundle, version)


def main() -> int:
    """Select the deployment destination and optionally preview or launch the result."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app-path",
        type=Path,
        default=Path.home() / "Applications/Conways Game of Life.app",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report install or update without writing or downloading anything.",
    )
    parser.add_argument(
        "--open", action="store_true", help="Launch after deployment succeeds."
    )
    arguments: argparse.Namespace = parser.parse_args()
    bundle: Path = Path(os.path.abspath(arguments.app_path.expanduser()))
    try:
        validate_host()
        action: str = deployment_action(bundle)
        version: str = str(
            runpy.run_path(str(ROOT / "src/gameoflife/__init__.py"))["__version__"]
        )
        print(f"{action} Conway's Game of Life {version}: {bundle}", flush=True)
        if arguments.dry_run:
            print(
                "Would synchronize .venv from requirements.txt, check dependencies "
                "and legal hashes, build, then verify and install the application.",
                flush=True,
            )
            return 0
        deploy(bundle, version)
        print(f"{action} complete: {bundle}", flush=True)
        if arguments.open:
            run("/usr/bin/open", str(bundle))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Deployment failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
