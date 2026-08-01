"""A macOS-friendly desktop implementation of Conway's Game of Life."""

from __future__ import annotations

import random
import sys
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Final, Protocol, cast

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QIcon,
    QKeySequence,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
)

from gameoflife import __version__
from gameoflife.life import Cell, LifeUniverse
from gameoflife.life_canvas import LifeCanvas
from gameoflife.patterns import PATTERNS

APP_NAME: Final[str] = "Conway's Game of Life"
AUTHOR: Final[str] = "Greg Pfountz"
BUILD_DATE: Final[str] = "July 26, 2026"
VERSION: Final[str] = __version__
ICON_FILE_NAME: Final[str] = "conways-life-icon.png"
INSTALLED_ASSET_DIRECTORY: Final[Path] = Path("share/conways-game-of-life")
WINDOW_SIZE_SCALE: Final[float] = 0.8
DEFAULT_INTERVAL_MS: Final[int] = 180
NEW_WINDOW_WIDTH: Final[int] = 50
NEW_WINDOW_HEIGHT: Final[int] = 40
NEW_WINDOW_FILL_WIDTH: Final[int] = 44
NEW_WINDOW_FILL_HEIGHT: Final[int] = 34
NEW_WINDOW_RANDOM_FILL_PROBABILITY: Final[float] = 0.28

class MacOSBundle(Protocol):
    """The Cocoa bundle operations needed to customize the app menu name."""

    def localizedInfoDictionary(self) -> MutableMapping[str, str] | None:
        """Return localized mutable metadata for the running application bundle."""
        ...

    def infoDictionary(self) -> MutableMapping[str, str] | None:
        """Return mutable metadata for the running application bundle."""
        ...


def application_icon_path() -> Path:
    """Return the icon next to source code or its installed wheel location."""
    source_icon: Path = Path(__file__).parent / "assets" / ICON_FILE_NAME
    if source_icon.is_file():
        return source_icon
    return Path(sys.prefix) / INSTALLED_ASSET_DIRECTORY / ICON_FILE_NAME


def configure_macos_bundle_name() -> None:
    """Set the Cocoa menu-bar name before Qt initializes its native menu."""
    if sys.platform != "darwin":
        return

    from Foundation import NSBundle  # pyright: ignore[reportAttributeAccessIssue]

    bundle: MacOSBundle = cast(MacOSBundle, NSBundle.mainBundle())
    bundle_info: MutableMapping[str, str] | None = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    if bundle_info is not None:
        bundle_info["CFBundleDisplayName"] = APP_NAME
        bundle_info["CFBundleName"] = APP_NAME


class MainWindow(QMainWindow):
    """The main native-menu window and simulation controller."""

    def __init__(self) -> None:
        """Create the main simulation window and its native menu actions."""
        super().__init__()
        self.universe: LifeUniverse = LifeUniverse()
        self.canvas: LifeCanvas = LifeCanvas(self.universe,
                                             min(self.width() / NEW_WINDOW_WIDTH,
                                                 self.height() / NEW_WINDOW_HEIGHT))
        self.timer: QTimer = QTimer(self)
        self.timer.setInterval(DEFAULT_INTERVAL_MS)
        self.timer.timeout.connect(self.step)
        self.new_action: QAction
        self.clear_action: QAction
        self.step_action: QAction
        self.run_action: QAction
        self.pan_left_action: QAction
        self.pan_right_action: QAction
        self.pan_up_action: QAction
        self.pan_down_action: QAction
        self.zoom_in_action: QAction
        self.zoom_out_action: QAction
        self.center_action: QAction
        self.about_action: QAction
        self.speed_actions: QActionGroup = QActionGroup(self)
        self.status: QStatusBar
        self.cell_size: float = min(self.width() / NEW_WINDOW_WIDTH,
                                    self.height() / NEW_WINDOW_HEIGHT)

        self.setWindowTitle(APP_NAME)
        self.settings = QSettings("com.pfountz", "ConwaysGameOfLife")
        # Restore geometry if it exists
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
            _zoom_amount: float = min(self.width() / NEW_WINDOW_WIDTH,
                                      self.height() / NEW_WINDOW_HEIGHT) / self.cell_size
            self.canvas.zoom(_zoom_amount)  # Ensure cell size is set correctly after window resize
            self.cell_size = min(self.width() / NEW_WINDOW_WIDTH,
                                 self.height() / NEW_WINDOW_HEIGHT)
        else:
            self.resize(int(QApplication.primaryScreen().size().width() * WINDOW_SIZE_SCALE),
                        int(QApplication.primaryScreen().size().height() * WINDOW_SIZE_SCALE))
        self.setCentralWidget(self.canvas)
        self.canvas.changed.connect(self.update_status)
        self._create_actions()
        self._create_menus()
        self._create_status_bar()
        self.update_status()
        QTimer.singleShot(0, self.new_universe)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save geometry when the window is closed."""
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        _old_cell_size = self.cell_size
        self.cell_size = min(self.width() / NEW_WINDOW_WIDTH,
                             self.height() / NEW_WINDOW_HEIGHT)
        self.canvas.zoom(self.cell_size / _old_cell_size)
        super().resizeEvent(event)

    def action(
        self,
        label: str,
        shortcut: QKeySequence.StandardKey | Qt.Key | str | None,
        callback: Callable[[], None],
    ) -> QAction:
        """Create an action with an optional shortcut and callback."""
        created: QAction = QAction(label, self)
        if shortcut is not None:
            created.setShortcut(shortcut)
        created.triggered.connect(callback)
        return created

    def _create_actions(self) -> None:
        """Create every command used by menus and keyboard shortcuts."""
        self.new_action = self.action("New", "N", self.new_universe)
        self.clear_action = self.action("Clear", "C", self.clear)
        self.step_action = self.action("Step Forward", "S", self.step)
        self.run_action = self.action("Run", Qt.Key.Key_Space, self.toggle_running)
        self.run_action.setCheckable(True)
        self.pan_left_action = self.action(
            "Pan Left", Qt.Key.Key_Left, lambda: self.canvas.pan_by_cells(-1, 0)
        )
        self.pan_right_action = self.action(
            "Pan Right", Qt.Key.Key_Right, lambda: self.canvas.pan_by_cells(1, 0)
        )
        self.pan_up_action = self.action(
            "Pan Up", Qt.Key.Key_Up, lambda: self.canvas.pan_by_cells(0, -1)
        )
        self.pan_down_action = self.action(
            "Pan Down", Qt.Key.Key_Down, lambda: self.canvas.pan_by_cells(0, 1)
        )
        self.zoom_in_action = self.action("Zoom In", "=", lambda: self.canvas.zoom_in())
        self.zoom_out_action = self.action("Zoom Out", "-", lambda: self.canvas.zoom_out())
        self.center_action = self.action("Center Pattern", "0", self.canvas.center_on_cells)
        self.about_action = self.action("About Conway's Game of Life", None, self.show_about)

    def _create_menus(self) -> None:
        """Build the Game, Patterns, View, and Help native menus."""
        game_menu: QMenu = self.menuBar().addMenu("Game")
        game_menu.addActions((self.new_action, self.clear_action))
        game_menu.addSeparator()
        game_menu.addActions((self.run_action, self.step_action))
        game_menu.addSeparator()
        speed_menu: QMenu = game_menu.addMenu("Simulation Speed")
        for label, interval, key in (("Slow", 500, Qt.Key.Key_1),
                                     ("Normal", DEFAULT_INTERVAL_MS, Qt.Key.Key_2),
                                     ("Fast", 65, Qt.Key.Key_3)):
            speed_action: QAction = QAction(label, self, checkable=True)
            speed_action.setShortcut(key)
            speed_action.triggered.connect(
                lambda checked=False, value=interval: self.set_speed(value))
            speed_menu.addAction(speed_action)
            self.speed_actions.addAction(speed_action)
        self.speed_actions.actions()[1].setChecked(True)

        pattern_menu: QMenu = self.menuBar().addMenu("Patterns")
        for name, cells in PATTERNS.items():
            inserted_cells: tuple[Cell, ...] = cells
            pattern_action: QAction = QAction(name, self)
            pattern_action.triggered.connect(
                lambda checked=False, seed=inserted_cells: self.load_pattern(seed))
            pattern_menu.addAction(pattern_action)

        view_menu: QMenu = self.menuBar().addMenu("View")
        view_menu.addActions((self.zoom_in_action, self.zoom_out_action, self.center_action))
        pan_menu: QMenu = view_menu.addMenu("Pan")
        pan_menu.addActions((
            self.pan_left_action,
            self.pan_right_action,
            self.pan_up_action,
            self.pan_down_action))
        help_menu: QMenu = self.menuBar().addMenu("Help")
        help_menu.addAction(self.about_action)

    def _create_status_bar(self) -> None:
        """Create the status bar that reports simulation statistics."""
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

    def new_universe(self) -> None:
        """Replace the universe with a fresh randomized starting pattern."""
        self.pause()
        self.canvas.clear_transitions()
        _start_column: int = -NEW_WINDOW_FILL_WIDTH // 2
        _end_column: int = NEW_WINDOW_FILL_WIDTH + _start_column
        _start_row: int = -NEW_WINDOW_FILL_HEIGHT // 2
        _end_row: int = NEW_WINDOW_FILL_HEIGHT + _start_row
        _system_random: random.SystemRandom = random.SystemRandom()
        cells: set[Cell] = {
            (column, row)
            for column in range(_start_column, _end_column)
            for row in range(_start_row, _end_row)
            if _system_random.random() < NEW_WINDOW_RANDOM_FILL_PROBABILITY
        }
        self.universe.set_cells(cells)
        self.canvas.center_on_cells()
        self.update_status()

    def clear(self) -> None:
        """Clear the universe and stop simulation playback."""
        self.pause()
        self.canvas.clear_transitions()
        self.universe.clear()
        self.canvas.update()
        self.update_status()

    def load_pattern(self, cells: tuple[Cell, ...]) -> None:
        """Load a built-in pattern and center it in the viewport."""
        self.pause()
        self.canvas.clear_transitions()
        self.universe.set_cells(cells)
        self.canvas.center_on_cells()
        self.update_status()

    def step(self) -> None:
        """Advance the universe by one simultaneous generation."""
        previous_live_cells: set[Cell] = set(self.universe.live_cells)
        self.universe.advance()
        born_cells: set[Cell] = self.universe.live_cells - previous_live_cells
        died_cells: set[Cell] = previous_live_cells - self.universe.live_cells
        self.canvas.animate_generation_transition(born_cells, died_cells, self.timer.interval())
        self.update_status()

    def toggle_running(self) -> None:
        """Start or stop timer-driven simulation playback."""
        if self.timer.isActive():
            self.pause()
        else:
            self.timer.start()
            self.run_action.setText("Pause")
            self.run_action.setChecked(True)

    def pause(self) -> None:
        """Stop playback and restore the Run action label."""
        self.timer.stop()
        self.run_action.setText("Run")
        self.run_action.setChecked(False)

    def set_speed(self, interval: int) -> None:
        """Set the timer interval and update the selected speed command."""
        self.timer.setInterval(interval)
        speed_labels: dict[int, str] = {500: "slow", DEFAULT_INTERVAL_MS: "normal", 65: "fast"}
        for speed_action in self.speed_actions.actions():
            speed_action.setChecked(speed_action.text().lower() == speed_labels[interval])

    def update_status(self) -> None:
        """Show the current generation number and live-cell population."""
        self.status.showMessage(
            f"Generation: {self.universe.generation}    Population: {self.universe.population}")

    def show_about(self) -> None:
        """Display the app's version, author, and control summary."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME}\n\n"
            f"Author: {AUTHOR}\n"
            f"Build date: {BUILD_DATE}\n"
            f"Version: {__version__}\n\n"
            "Click cells to toggle life.\n"
            "Arrow keys to pan, "
             "+/- to zoom.\n\n"
            "Rules: a live cell survives with two or three neighbours; "
            "a dead cell is born with exactly three neighbours (B3/S23).",
        )


def main() -> int:
    """Create and run the macOS desktop application event loop."""
    configure_macos_bundle_name()
    application: QApplication = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_NAME)
    application.setOrganizationName(AUTHOR)
    icon_path: Path = application_icon_path()
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
    window: MainWindow = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
