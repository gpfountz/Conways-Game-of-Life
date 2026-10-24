# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Verify offline legal-resource behavior, byte preservation, and omission failures."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from gameoflife import legal
from scripts import check_legal_resources as checks

ROOT: Path = Path(__file__).resolve().parents[1]


def test_offline_license_is_the_canonical_full_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Legal notices must load outside the checkout's working directory."""
    monkeypatch.chdir(tmp_path)
    assert legal.license_text().encode("utf-8") == (ROOT / "LICENSE").read_bytes()
    assert "GPL-3.0-only" in legal.LEGAL_SUMMARY
    assert "2026 Greg Pfountz" in legal.LEGAL_SUMMARY
    assert "ABSOLUTELY NO WARRANTY" in legal.LEGAL_SUMMARY


def test_all_upstream_notices_are_preserved_and_displayable() -> None:
    """Every preserved third-party notice is covered by provenance and the legal view."""
    files: dict[str, bytes] = checks.required_files()
    manifest: dict[str, object] = json.loads(files["SOURCES.json"])
    assert manifest["schema_version"] == 1
    text: str = legal.third_party_text()
    for name, content in files.items():
        if name.startswith("third-party/"):
            assert content.decode("utf-8") in text, name


def test_missing_resource_produces_an_actionable_error() -> None:
    """Missing packaged text must fail clearly rather than silently omit a notice."""
    with pytest.raises(
        legal.LegalResourceError, match="Reinstall a complete application"
    ):
        legal.read_legal_text("missing-license.txt")


def test_corrupt_or_missing_upstream_notice_fails_verification(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A changed upstream notice cannot pass merely because its filename still exists."""
    import shutil

    resources: Path = tmp_path / "legal_texts"
    shutil.copytree(ROOT / "src/gameoflife/legal_texts", resources)
    monkeypatch.setattr(checks, "RESOURCES", resources)
    notice: Path = resources / "third-party/PyObjC/LICENSE.txt"
    notice.write_text("truncated MIT notice\n")
    with pytest.raises(ValueError, match="Preserved upstream notice changed"):
        checks.required_files()
    notice.unlink()
    with pytest.raises(KeyError):
        checks.required_files()


def test_wheel_omitting_legal_resources_is_rejected(tmp_path: Path) -> None:
    """Artifact verification must catch omissions even when metadata claims GPLv3."""
    wheel: Path = tmp_path / "incomplete.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(
            "gameoflife-1.0.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nLicense-Expression: GPL-3.0-only\nAuthor: Greg Pfountz\n",
        )
    with pytest.raises(KeyError):
        checks.check_wheel(wheel)
