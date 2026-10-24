# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Load the application's legal notices from installed, offline package resources."""

from __future__ import annotations

from importlib.resources import files
from typing import Final

LICENSE_IDENTIFIER: Final[str] = "GPL-3.0-only"
COPYRIGHT_NOTICE: Final[str] = "Copyright (C) 2026 Greg Pfountz"
LEGAL_SUMMARY: Final[str] = (
    f"{COPYRIGHT_NOTICE}\n"
    "GNU General Public License, version 3 only (GPL-3.0-only).\n"
    "You may redistribute and modify this program under that license.\n"
    "This program comes with ABSOLUTELY NO WARRANTY, to the extent permitted by law.\n"
    "Read the License and Third-party tabs for the full terms and notices."
)


class LegalResourceError(RuntimeError):
    """A required legal notice was omitted or cannot be read."""


def read_legal_text(relative_path: str) -> str:
    """Read an installed UTF-8 legal resource or raise an actionable error."""
    try:
        return (
            files("gameoflife")
            .joinpath("legal_texts", *relative_path.split("/"))
            .read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError) as error:
        raise LegalResourceError(
            f"Required legal notice '{relative_path}' is unavailable. "
            "Reinstall a complete application package."
        ) from error


def license_text() -> str:
    """Return the full unmodified GPLv3 text without requiring network access."""
    return read_legal_text("LICENSE")


def third_party_text() -> str:
    """Combine the notice index and its complete preserved upstream texts."""
    names: tuple[str, ...] = (
        "THIRD_PARTY_NOTICES.md",
        "third-party/PySide6/GPL-3.0-only.txt",
        "third-party/PySide6/LGPL-3.0-only.txt",
        "third-party/PySide6/GPL-2.0-only.txt",
        "third-party/PySide6/Apache-2.0.txt",
        "third-party/PySide6/BSD-3-Clause.txt",
        "third-party/PySide6/Qt-GPL-exception-1.0.txt",
        "third-party/PySide6/GFDL-1.3-no-invariants-only.txt",
        "third-party/PyObjC/LICENSE.txt",
        "third-party/FFmpeg/COPYING.LGPLv2.1",
        "third-party/FFmpeg/LICENSE.md",
        "third-party/Python/LICENSE",
    )
    return "\n\n".join(f"{name}\n{'=' * 72}\n{read_legal_text(name)}" for name in names)
