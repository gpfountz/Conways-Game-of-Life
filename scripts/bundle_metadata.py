"""Write macOS metadata using the shared application version."""

from __future__ import annotations

import argparse
import plistlib
import runpy
from pathlib import Path
from typing import Any


def update_bundle(bundle: Path) -> None:
    """Create or refresh application metadata without changing its build identifier."""
    version: str = str(
        runpy.run_path(
            str(Path(__file__).resolve().parents[1] / "src/gameoflife/__init__.py")
        )["__version__"]
    )
    path: Path = bundle / "Contents/Info.plist"
    metadata: dict[str, Any] = (
        plistlib.loads(path.read_bytes()) if path.exists() else {}
    )
    metadata.update(
        {
            "CFBundleDisplayName": "Conway's Game of Life",
            "CFBundleExecutable": "conways-game-of-life",
            "CFBundleIdentifier": "com.greg.conwaysgameoflife",
            "CFBundleIconFile": "ConwaysGameOfLife",
            "CFBundleName": "Conway's Game of Life",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": version,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(metadata, sort_keys=False))


def main() -> None:
    """Update the bundle selected explicitly by the deployment workflow."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    arguments: argparse.Namespace = parser.parse_args()
    update_bundle(arguments.bundle)


if __name__ == "__main__":
    main()
