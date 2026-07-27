"""A macOS-friendly desktop implementation of Conway's Game of Life."""

from __future__ import annotations

import random
import sys
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Final, Protocol, cast

from PySide6.QtCore import QElapsedTimer, QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QStatusBar,
    QWidget,
)

from life import Cell, LifeUniverse, cells_on_line
from patterns import PATTERNS

CELL_SIZE: Final[float] = 18.0
MIN_CELL_SIZE: Final[float] = 4.0
MAX_CELL_SIZE: Final[float] = 64.0
DEFAULT_INTERVAL_MS: Final[int] = 180
PAN_INCREMENT_CELLS: Final[int] = 4
ANIMATION_FRAME_INTERVAL_MS: Final[int] = 16
BACKGROUND_COLOR: Final[QColor] = QColor("#000000")
GRID_COLOR: Final[QColor] = QColor(90, 90, 90, 115)
APP_NAME: Final[str] = "Conway's Game of Life"
AUTHOR: Final[str] = "Greg Pfountz"
BUILD_DATE: Final[str] = "July 26, 2026"
VERSION: Final[str] = "1.0.11"
ICON_FILE_NAME: Final[str] = "conways-life-icon.png"
INSTALLED_ASSET_DIRECTORY: Final[Path] = Path("share/conways-game-of-life")


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

    from Foundation import NSBundle

    bundle: MacOSBundle = cast(MacOSBundle, NSBundle.mainBundle())
    bundle_info: MutableMapping[str, str] | None = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    if bundle_info is not None:
        bundle_info["CFBundleDisplayName"] = APP_NAME
        bundle_info["CFBundleName"] = APP_NAME


class LifeCanvas(QWidget):
    """Pannable, zoomable viewport over a sparse infinite Life universe."""

    changed: Signal = Signal()

    def __init__(self, universe: LifeUniverse, parent: QWidget | None = None) -> None:
        """Create a canvas that displays and edits a Life universe."""
        super().__init__(parent)
        self.universe: LifeUniverse = universe
        self.cell_size: float = CELL_SIZE
        self.origin: QPointF = QPointF()
        self._last_drag_position: QPointF | None = None
        self._last_toggled_cell: Cell | None = None
        self._drag_button: Qt.MouseButton | None = None
        self._dragging: bool = False
        self._toggled_cells: set[Cell] = set()
        self._birth_cells: set[Cell] = set()
        self._death_cells: set[Cell] = set()
        self._transition_duration_ms: int = DEFAULT_INTERVAL_MS
        self._transition_clock: QElapsedTimer = QElapsedTimer()
        self._animation_timer: QTimer = QTimer(self)
        self._animation_timer.setInterval(ANIMATION_FRAME_INTERVAL_MS)
        self._animation_timer.timeout.connect(self._advance_transition)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def showEvent(self, event: QEvent) -> None:
        """Center the empty universe when the canvas first becomes visible."""
        super().showEvent(event)
        if self.origin.isNull():
            self.origin = QPointF(self.width() / 2, self.height() / 2)

    def cell_at(self, point: QPointF) -> Cell:
        """Convert a canvas point to its corresponding grid cell."""
        column: int = int((point.x() - self.origin.x()) // self.cell_size)
        row: int = int((point.y() - self.origin.y()) // self.cell_size)
        return column, row

    def cell_rect(self, cell: Cell) -> QRectF:
        """Return the on-screen rectangle occupied by one grid cell."""
        column, row = cell
        return QRectF(
            self.origin.x() + column * self.cell_size,
            self.origin.y() + row * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def center_on_cells(self) -> None:
        """Move the viewport so the live-cell pattern is centered."""
        if not self.universe.live_cells:
            self.origin = QPointF(self.width() / 2, self.height() / 2)
            self.update()
            return
        average_column: float = sum(cell[0] for cell in self.universe.live_cells) / self.universe.population
        average_row: float = sum(cell[1] for cell in self.universe.live_cells) / self.universe.population
        self.origin = QPointF(
            self.width() / 2 - average_column * self.cell_size,
            self.height() / 2 - average_row * self.cell_size,
        )
        self.update()

    def zoom(self, multiplier: float, focus: QPointF | None = None) -> None:
        """Scale the viewport around an optional focus point."""
        focus_point: QPointF = focus or QPointF(self.width() / 2, self.height() / 2)
        old_size: float = self.cell_size
        new_size: float = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, old_size * multiplier))
        if new_size == old_size:
            return
        cell_x: float = (focus_point.x() - self.origin.x()) / old_size
        cell_y: float = (focus_point.y() - self.origin.y()) / old_size
        self.cell_size = new_size
        self.origin = QPointF(focus_point.x() - cell_x * new_size, focus_point.y() - cell_y * new_size)
        self.update()

    def pan_by_cells(self, column_offset: int, row_offset: int) -> None:
        """Move the viewport by a fixed number of cells."""
        self.origin -= QPointF(column_offset * self.cell_size, row_offset * self.cell_size)
        self.update()

    def animate_generation_transition(
        self,
        born_cells: set[Cell],
        died_cells: set[Cell],
        duration_ms: int,
    ) -> None:
        """Animate births into view and deaths away over one generation interval."""
        self._birth_cells = set(born_cells)
        self._death_cells = set(died_cells)
        self._transition_duration_ms = max(1, duration_ms)
        if not self._birth_cells and not self._death_cells:
            self.clear_transitions()
            return
        self._transition_clock.start()
        self._animation_timer.start()
        self.update()

    def clear_transitions(self) -> None:
        """Stop any pending birth or death animations and redraw stable cells."""
        self._animation_timer.stop()
        self._transition_clock.invalidate()
        self._birth_cells.clear()
        self._death_cells.clear()
        self.update()

    def _transition_progress(self) -> float:
        """Return the normalized progress of the active generation transition."""
        if not self._transition_clock.isValid():
            return 1.0
        elapsed_ms: int = self._transition_clock.elapsed()
        return min(1.0, elapsed_ms / self._transition_duration_ms)

    def _advance_transition(self) -> None:
        """Request animation frames until the birth and death transition completes."""
        if self._transition_progress() >= 1.0:
            self._animation_timer.stop()
            self._transition_clock.invalidate()
            self._birth_cells.clear()
            self._death_cells.clear()
        self.update()

    def _draw_cell(
        self,
        painter: QPainter,
        cell: Cell,
        color: QColor,
        facing_scale: float = 1.0,
        opacity: float = 1.0,
    ) -> None:
        """Draw a cell with optional horizontal flip scale and opacity."""
        if facing_scale <= 0.0 or opacity <= 0.0:
            return
        base_rectangle: QRectF = self.cell_rect(cell).adjusted(1.0, 1.0, -1.0, -1.0)
        visible_width: float = base_rectangle.width() * min(1.0, facing_scale)
        visible_left: float = base_rectangle.center().x() - visible_width / 2
        visible_rectangle: QRectF = QRectF(
            visible_left,
            base_rectangle.top(),
            visible_width,
            base_rectangle.height(),
        )
        cell_color: QColor = QColor(color)
        cell_color.setAlphaF(min(1.0, opacity))
        painter.setBrush(cell_color)
        painter.drawRect(visible_rectangle)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the visible grid and every visible live cell."""
        del event
        painter: QPainter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND_COLOR)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.cell_size >= 8.0:
            painter.setPen(QPen(GRID_COLOR, 1.0))
            start_column: int = int((-self.origin.x()) // self.cell_size) - 1
            end_column: int = int((self.width() - self.origin.x()) // self.cell_size) + 1
            start_row: int = int((-self.origin.y()) // self.cell_size) - 1
            end_row: int = int((self.height() - self.origin.y()) // self.cell_size) + 1
            for column in range(start_column, end_column + 1):
                x: float = self.origin.x() + column * self.cell_size
                painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            for row in range(start_row, end_row + 1):
                y: float = self.origin.y() + row * self.cell_size
                painter.drawLine(QPointF(0, y), QPointF(self.width(), y))

        live_color: QColor = self.palette().highlight().color()
        painter.setPen(Qt.PenStyle.NoPen)
        transition_progress: float = self._transition_progress()
        stable_cells: set[Cell] = self.universe.live_cells - self._birth_cells
        for cell in stable_cells:
            self._draw_cell(painter, cell, live_color)
        for cell in self._birth_cells:
            self._draw_cell(painter, cell, live_color, transition_progress, transition_progress)
        death_scale: float = 1.0 - transition_progress
        for cell in self._death_cells:
            self._draw_cell(painter, cell, live_color, death_scale, death_scale)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start a cell-edit stroke or a mouse-button pan gesture."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_button = event.button()
            self._last_toggled_cell = self.cell_at(event.position())
            self._toggled_cells.clear()
            self._toggle_cell(self._last_toggled_cell)
        elif event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._drag_button = event.button()
            self._dragging = True
            self._last_drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Extend a cell-edit stroke or pan while a mouse button is held."""
        if self._drag_button == Qt.MouseButton.LeftButton and self._last_toggled_cell is not None:
            current_cell: Cell = self.cell_at(event.position())
            for cell in cells_on_line(self._last_toggled_cell, current_cell):
                self._toggle_cell(cell)
            self._last_toggled_cell = current_cell
            return

        if self._last_drag_position is not None and self._drag_button is not None:
            if not self._dragging:
                return
            offset: QPointF = event.position() - self._last_drag_position
            self.origin += offset
            self._last_drag_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish an active edit stroke or panning gesture."""
        if event.button() == self._drag_button:
            self._dragging = False
            self._last_drag_position = None
            self._last_toggled_cell = None
            self._toggled_cells.clear()
            self._drag_button = None
            self.unsetCursor()

    def _toggle_cell(self, cell: Cell) -> None:
        """Toggle a cell at most once during the current left-button stroke."""
        if cell in self._toggled_cells:
            return
        self.clear_transitions()
        self.universe.toggle(cell)
        self._toggled_cells.add(cell)
        self.changed.emit()
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom the viewport in response to a scroll-wheel gesture."""
        multiplier: float = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.zoom(multiplier, event.position())


class MainWindow(QMainWindow):
    """The main native-menu window and simulation controller."""

    def __init__(self) -> None:
        """Create the main simulation window and its native menu actions."""
        super().__init__()
        self.universe: LifeUniverse = LifeUniverse()
        self.canvas: LifeCanvas = LifeCanvas(self.universe)
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
        self.speed_actions: list[QAction] = []
        self.status: QStatusBar

        self.setWindowTitle(APP_NAME)
        self.resize(960, 700)
        self.setCentralWidget(self.canvas)
        self.canvas.changed.connect(self.update_status)
        self._create_actions()
        self._create_menus()
        self._create_status_bar()
        self.update_status()
        QTimer.singleShot(0, self.new_universe)

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
            "Pan Left", Qt.Key.Key_Left, lambda: self.canvas.pan_by_cells(-PAN_INCREMENT_CELLS, 0)
        )
        self.pan_right_action = self.action(
            "Pan Right", Qt.Key.Key_Right, lambda: self.canvas.pan_by_cells(PAN_INCREMENT_CELLS, 0)
        )
        self.pan_up_action = self.action(
            "Pan Up", Qt.Key.Key_Up, lambda: self.canvas.pan_by_cells(0, -PAN_INCREMENT_CELLS)
        )
        self.pan_down_action = self.action(
            "Pan Down", Qt.Key.Key_Down, lambda: self.canvas.pan_by_cells(0, PAN_INCREMENT_CELLS)
        )
        self.zoom_in_action = self.action("Zoom In", "=", lambda: self.canvas.zoom(1.18))
        self.zoom_out_action = self.action("Zoom Out", "-", lambda: self.canvas.zoom(1 / 1.18))
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
        for label, interval, key in (("Slow", 500, Qt.Key_1), ("Normal", DEFAULT_INTERVAL_MS, Qt.Key_2), ("Fast", 65, Qt.Key_3)):
            speed_action: QAction = QAction(label, self, checkable=True)
            speed_action.setShortcut(key)
            speed_action.triggered.connect(lambda checked=False, value=interval: self.set_speed(value))
            speed_menu.addAction(speed_action)
            self.speed_actions.append(speed_action)
        self.speed_actions[1].setChecked(True)

        pattern_menu: QMenu = self.menuBar().addMenu("Patterns")
        for name, cells in PATTERNS.items():
            inserted_cells: tuple[Cell, ...] = cells
            pattern_action: QAction = QAction(name, self)
            pattern_action.triggered.connect(lambda checked=False, seed=inserted_cells: self.load_pattern(seed))
            pattern_menu.addAction(pattern_action)

        view_menu: QMenu = self.menuBar().addMenu("View")
        view_menu.addActions((self.zoom_in_action, self.zoom_out_action, self.center_action))
        pan_menu: QMenu = view_menu.addMenu("Pan")
        pan_menu.addActions((self.pan_left_action, self.pan_right_action, self.pan_up_action, self.pan_down_action))

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
        cells: set[Cell] = {
            (column, row)
            for column in range(-22, 23)
            for row in range(-16, 17)
            if random.random() < 0.28
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
        for speed_action in self.speed_actions:
            speed_action.setChecked(speed_action.text().lower() == speed_labels[interval])

    def update_status(self) -> None:
        """Show the current generation number and live-cell population."""
        self.status.showMessage(f"Generation: {self.universe.generation}    Population: {self.universe.population}")

    def show_about(self) -> None:
        """Display the app's version, author, and control summary."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME}\n\n"
            f"Author: {AUTHOR}\n"
            f"Build date: {BUILD_DATE}\n"
            f"Version: {VERSION}\n\n"
            "Click cells to toggle life. Drag to pan, use the arrow keys to pan, or scroll to zoom.\n\n"
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
    return cast(int, application.exec())


if __name__ == "__main__":
    raise SystemExit(main())
