# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Opt-in native Qt verification of themed legal documents in an isolated profile."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_QT_LEGAL_TESTS") != "1",
    reason="Native Qt verification is opt-in; use RUN_QT_LEGAL_TESTS=1 with an offscreen platform.",
)


@pytest.fixture
def application(tmp_path: Path) -> Iterator[QApplication]:
    """Keep test preferences separate from the user's normal application settings."""
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    app: QApplication = cast(QApplication, QApplication.instance() or QApplication([]))
    app.setApplicationName("Conways Legal Verification")
    app.setOrganizationName("Conways Legal Verification")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path)
    )
    yield app
    app.closeAllWindows()
    app.processEvents()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_legal_dialog_readability_and_scrolling(
    application: QApplication, theme: str, tmp_path: Path
) -> None:
    """Render both themes and verify the complete license/notices remain readable and selectable."""
    from PySide6.QtGui import QColor, QPalette, QTextCursor
    from PySide6.QtWidgets import QTextBrowser

    from gameoflife.legal import LEGAL_SUMMARY, license_text, third_party_text
    from gameoflife.legal_dialog import LegalDialog

    palette: QPalette = QPalette()
    foreground: QColor = QColor("#ededed" if theme == "dark" else "#171717")
    background: QColor = QColor("#242424" if theme == "dark" else "#fafafa")
    for role in (
        QPalette.ColorRole.Window,
        QPalette.ColorRole.Base,
        QPalette.ColorRole.Button,
    ):
        palette.setColor(role, background)
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(role, foreground)
    application.setPalette(palette)
    dialog: LegalDialog = LegalDialog(
        "About Conway's Game of Life", "Isolated legal verification"
    )
    dialog.show()
    application.processEvents()
    assert "Greg Pfountz" in LEGAL_SUMMARY
    directory: Path = Path(os.environ.get("LEGAL_QA_DIRECTORY", str(tmp_path)))
    directory.mkdir(parents=True, exist_ok=True)
    for index, expected, name in (
        (1, license_text(), "license"),
        (2, third_party_text(), "third-party"),
    ):
        dialog.tabs.setCurrentIndex(index)
        application.processEvents()
        browser: QTextBrowser = cast(QTextBrowser, dialog.tabs.widget(index))
        assert browser.isReadOnly()
        assert browser.toPlainText() == expected
        assert browser.verticalScrollBar().maximum() > 0
        browser.selectAll()
        assert browser.textCursor().hasSelection()
        browser.moveCursor(QTextCursor.MoveOperation.Start)
        application.processEvents()
        assert dialog.grab().save(str(directory / f"{theme}-{name}.png"))
        browser.moveCursor(QTextCursor.MoveOperation.End)
        application.processEvents()
        assert browser.verticalScrollBar().value() > 0
    dialog.close()


def test_missing_notices_report_error_without_changing_game(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A packaging failure must display a clear error and preserve the running universe."""
    from PySide6.QtWidgets import QMessageBox

    from gameoflife import legal_dialog
    from gameoflife.legal import LegalResourceError
    from gameoflife.main import MainWindow

    def missing_license() -> str:
        """Simulate an omitted runtime GPL text in an otherwise installed application."""
        raise LegalResourceError("Required legal notice 'LICENSE' is unavailable.")

    errors: list[str] = []

    def report_error(parent: MainWindow, title: str, message: str) -> None:
        """Capture the visible failure without opening a blocking native message box."""
        errors.append(f"{title}: {message}")

    monkeypatch.setattr(legal_dialog, "license_text", missing_license)
    monkeypatch.setattr(QMessageBox, "critical", report_error)
    window: MainWindow = MainWindow()
    window.universe.set_cells({(1, 2), (2, 2), (3, 2)})
    window.show_about()
    assert window.universe.live_cells == {(1, 2), (2, 2), (3, 2)}
    assert window.universe.generation == 0
    assert len(errors) == 1 and "Legal notices unavailable" in errors[0]
    window.close()
