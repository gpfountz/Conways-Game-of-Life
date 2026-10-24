# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Verify canonical notices and their inclusion in real package artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from email.message import Message
from email.parser import BytesParser
from pathlib import Path
from typing import IO, Any
from zipfile import ZipFile

ROOT: Path = Path(__file__).resolve().parents[1]
RESOURCES: Path = ROOT / "src/gameoflife/legal_texts"


def required_files() -> dict[str, bytes]:
    """Validate upstream hashes and return every required runtime legal document."""
    files: dict[str, bytes] = {
        path.relative_to(RESOURCES).as_posix(): path.read_bytes()
        for path in RESOURCES.rglob("*")
        if path.is_file()
    }
    if files.get("LICENSE") != (ROOT / "LICENSE").read_bytes():
        raise ValueError("Offline GPL text differs from the canonical LICENSE.")
    manifest: dict[str, Any] = json.loads(files["SOURCES.json"])
    for entry in manifest["upstream_notices"]:
        path: str = entry["path"]
        if hashlib.sha256(files[path]).hexdigest() != entry["sha256"]:
            raise ValueError(f"Preserved upstream notice changed: {path}")
    declared: set[str] = {entry["path"] for entry in manifest["upstream_notices"]}
    actual: set[str] = {path for path in files if path.startswith("third-party/")}
    if actual != declared:
        raise ValueError("Upstream notice files and provenance records disagree.")
    if not files.get("THIRD_PARTY_NOTICES.md"):
        raise ValueError("The third-party notice index is missing.")
    return files


def check_wheel(path: Path) -> None:
    """Require offline resources, legal metadata, and exact upstream bytes in a wheel."""
    expected: dict[str, bytes] = required_files()
    with ZipFile(path) as archive:
        names: list[str] = archive.namelist()
        metadata_path: str = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        message: Message = BytesParser().parsebytes(archive.read(metadata_path))
        if message["License-Expression"] != "GPL-3.0-only":
            raise ValueError("Wheel does not declare GPL-3.0-only.")
        if "Greg Pfountz" not in str(message["Author"]):
            raise ValueError("Wheel is missing the project author credit.")
        prefix: str = metadata_path.rsplit("/", 1)[0] + "/licenses/"
        for name, content in expected.items():
            if archive.read(f"gameoflife/legal_texts/{name}") != content:
                raise ValueError(f"Wheel runtime legal resource changed: {name}")
        if archive.read(prefix + "LICENSE") != (ROOT / "LICENSE").read_bytes():
            raise ValueError("Wheel metadata LICENSE differs from the canonical text.")
        for entry in json.loads(expected["SOURCES.json"])["upstream_notices"]:
            name = entry["path"]
            metadata_name: str = f"src/gameoflife/legal_texts/{name}"
            if metadata_name not in message.get_all("License-File", []):
                raise ValueError(f"Wheel legal metadata omits {name}")
            if archive.read(prefix + metadata_name) != expected[name]:
                raise ValueError(f"Wheel metadata notice changed: {name}")


def check_sdist(path: Path) -> None:
    """Require legal resources and the project's build/install materials in an sdist."""
    expected: dict[str, bytes] = required_files()
    with tarfile.open(path) as archive:
        names: list[str] = archive.getnames()
        prefix: str = names[0].split("/", 1)[0] + "/"
        for name in (
            "LICENSE",
            "LICENSING.md",
            "pyproject.toml",
            "requirements.txt",
            "redeploy.sh",
            "scripts/bundle_metadata.py",
            "scripts/app_versioning.py",
            "scripts/check_legal_resources.py",
            "AGENTS.md",
            "tests/test_legal.py",
        ):
            resource: IO[bytes] | None = archive.extractfile(prefix + name)
            if resource is None or resource.read() != (ROOT / name).read_bytes():
                raise ValueError(f"Source distribution omits or changes {name}")
        for name, content in expected.items():
            resource = archive.extractfile(
                prefix + "src/gameoflife/legal_texts/" + name
            )
            if resource is None or resource.read() != content:
                raise ValueError(f"Source distribution legal resource changed: {name}")


def main() -> int:
    """Check the checkout and any explicitly selected wheel or source archive."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    arguments: argparse.Namespace = parser.parse_args()
    try:
        required_files()
        if arguments.wheel:
            check_wheel(arguments.wheel)
        if arguments.sdist:
            check_sdist(arguments.sdist)
    except (OSError, ValueError, KeyError, StopIteration) as error:
        print(f"Legal resource verification failed: {error}")
        return 1
    print(
        "Legal resources and selected artifact contents verified; binary release review remains separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
