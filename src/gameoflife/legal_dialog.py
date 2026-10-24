# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
"""Present readable, selectable legal notices using native themed Qt widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gameoflife.legal import LEGAL_SUMMARY, license_text, third_party_text


class LegalDialog(QDialog):
    """An offline About dialog with full license and dependency notices."""

    def __init__(self, title: str, about: str, parent: QWidget | None = None) -> None:
        """Load required notices before opening a state-independent modal dialog."""
        license_document: str = license_text()
        third_party_document: str = third_party_text()
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 620)
        layout: QVBoxLayout = QVBoxLayout(self)
        notice: QLabel = QLabel(LEGAL_SUMMARY, self)
        notice.setTextFormat(Qt.TextFormat.PlainText)
        notice.setWordWrap(True)
        notice.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        notice.setAccessibleName("Copyright and license notice")
        layout.addWidget(notice)
        self.tabs: QTabWidget = QTabWidget(self)
        self.tabs.setAccessibleName("About and legal documents")
        self.add_document("About", about)
        self.add_document("License", license_document)
        self.add_document("Third-party", third_party_document)
        layout.addWidget(self.tabs)
        buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_document(self, title: str, text: str) -> None:
        """Add one selectable, scrollable document without executing markup or links."""
        browser: QTextBrowser = QTextBrowser(self.tabs)
        browser.setAccessibleName(f"{title} text")
        browser.setPlainText(text)
        self.tabs.addTab(browser, title)
