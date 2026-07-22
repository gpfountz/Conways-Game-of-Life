"""A macOS-friendly desktop implementation of Conway's Game of Life."""

from __future__ import annotations

import random
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStatusBar,
    QWidget,
)

from life import Cell, LifeUniverse, cells_on_line
from patterns import PATTERNS

CELL_SIZE = 18.0
MIN_CELL_SIZE = 4.0
MAX_CELL_SIZE = 64.0
DEFAULT_INTERVAL_MS = 180
PAN_INCREMENT_CELLS = 4
BACKGROUND_COLOR = QColor("#000000")
GRID_COLOR = QColor(90, 90, 90, 115)
APP_NAME = "Conway's Game of Life"
AUTHOR = "Greg Pfountz"
BUILD_DATE = "July 22, 2026"
VERSION = "1.0.9"
ICON_FILE_NAME = "conways-life-icon.png"
INSTALLED_ASSET_DIRECTORY = Path("share/conways-game-of-life")


def application_icon_path() -> Path:
    """Return the icon next to source code or its installed wheel location."""
    source_icon = Path(__file__).parent / "assets" / ICON_FILE_NAME
    if source_icon.is_file():
        return source_icon
    return Path(sys.prefix) / INSTALLED_ASSET_DIRECTORY / ICON_FILE_NAME


def configure_macos_bundle_name() -> None:
    """Set the Cocoa menu-bar name before Qt initializes its native menu."""
    if sys.platform != "darwin":
        return

    from Foundation import NSBundle

    bundle = NSBundle.mainBundle()
    bundle_info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    if bundle_info is not None:
        bundle_info["CFBundleDisplayName"] = APP_NAME
        bundle_info["CFBundleName"] = APP_NAME


class LifeCanvas(QWidget):
    """Pannable, zoomable viewport over a sparse infinite Life universe."""

    changed = Signal()

    def __init__(self, universe: LifeUniverse, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.universe = universe
        self.cell_size: float = CELL_SIZE
        self.origin: QPointF = QPointF()
        self._last_drag_position: QPointF | None = None
        self._last_toggled_cell: Cell | None = None
        self._drag_button: Qt.MouseButton | None = None
        self._dragging: bool = False
        self._toggled_cells: set[Cell] = set()
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event)
        if self.origin.isNull():
            self.origin = QPointF(self.width() / 2, self.height() / 2)

    def cell_at(self, point: QPointF) -> Cell:
        column = int((point.x() - self.origin.x()) // self.cell_size)
        row = int((point.y() - self.origin.y()) // self.cell_size)
        return column, row

    def cell_rect(self, cell: Cell) -> QRectF:
        column, row = cell
        return QRectF(
            self.origin.x() + column * self.cell_size,
            self.origin.y() + row * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def center_on_cells(self) -> None:
        if not self.universe.live_cells:
            self.origin = QPointF(self.width() / 2, self.height() / 2)
            self.update()
            return
        average_column = sum(cell[0] for cell in self.universe.live_cells) / self.universe.population
        average_row = sum(cell[1] for cell in self.universe.live_cells) / self.universe.population
        self.origin = QPointF(
            self.width() / 2 - average_column * self.cell_size,
            self.height() / 2 - average_row * self.cell_size,
        )
        self.update()

    def zoom(self, multiplier: float, focus: QPointF | None = None) -> None:
        focus_point = focus or QPointF(self.width() / 2, self.height() / 2)
        old_size = self.cell_size
        new_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, old_size * multiplier))
        if new_size == old_size:
            return
        cell_x = (focus_point.x() - self.origin.x()) / old_size
        cell_y = (focus_point.y() - self.origin.y()) / old_size
        self.cell_size = new_size
        self.origin = QPointF(focus_point.x() - cell_x * new_size, focus_point.y() - cell_y * new_size)
        self.update()

    def pan_by_cells(self, column_offset: int, row_offset: int) -> None:
        """Move the viewport by a fixed number of cells."""
        self.origin -= QPointF(column_offset * self.cell_size, row_offset * self.cell_size)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND_COLOR)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.cell_size >= 8.0:
            painter.setPen(QPen(GRID_COLOR, 1.0))
            start_column = int((-self.origin.x()) // self.cell_size) - 1
            end_column = int((self.width() - self.origin.x()) // self.cell_size) + 1
            start_row = int((-self.origin.y()) // self.cell_size) - 1
            end_row = int((self.height() - self.origin.y()) // self.cell_size) + 1
            for column in range(start_column, end_column + 1):
                x = self.origin.x() + column * self.cell_size
                painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            for row in range(start_row, end_row + 1):
                y = self.origin.y() + row * self.cell_size
                painter.drawLine(QPointF(0, y), QPointF(self.width(), y))

        live_color = self.palette().highlight().color()
        painter.setBrush(live_color)
        painter.setPen(Qt.PenStyle.NoPen)
        for cell in self.universe.live_cells:
            rectangle = self.cell_rect(cell).adjusted(1.0, 1.0, -1.0, -1.0)
            if rectangle.intersects(QRectF(self.rect())):
                painter.drawRect(rectangle)

    def mousePressEvent(self, event: QMouseEvent) -> None:
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
        if self._drag_button == Qt.MouseButton.LeftButton and self._last_toggled_cell is not None:
            current_cell = self.cell_at(event.position())
            for cell in cells_on_line(self._last_toggled_cell, current_cell):
                self._toggle_cell(cell)
            self._last_toggled_cell = current_cell
            return

        if self._last_drag_position is not None and self._drag_button is not None:
            if not self._dragging:
                return
            offset = event.position() - self._last_drag_position
            self.origin += offset
            self._last_drag_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
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
        self.universe.toggle(cell)
        self._toggled_cells.add(cell)
        self.changed.emit()
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        multiplier = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.zoom(multiplier, event.position())


class MainWindow(QMainWindow):
    """The main native-menu window and simulation controller."""

    def __init__(self) -> None:
        super().__init__()
        self.universe = LifeUniverse()
        self.canvas = LifeCanvas(self.universe)
        self.timer = QTimer(self)
        self.timer.setInterval(DEFAULT_INTERVAL_MS)
        self.timer.timeout.connect(self.step)
        self.run_action: QAction
        self.speed_actions: list[QAction] = []

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
        created = QAction(label, self)
        if shortcut is not None:
            created.setShortcut(shortcut)
        created.triggered.connect(callback)
        return created

    def _create_actions(self) -> None:
        self.new_action = self.action("New", QKeySequence.StandardKey.New, self.new_universe)
        self.clear_action = self.action("Clear", None, self.clear)
        self.step_action = self.action("Step Forward", None, self.step)
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
        self.zoom_in_action = self.action("Zoom In", QKeySequence.StandardKey.ZoomIn, lambda: self.canvas.zoom(1.18))
        self.zoom_out_action = self.action("Zoom Out", QKeySequence.StandardKey.ZoomOut, lambda: self.canvas.zoom(1 / 1.18))
        self.center_action = self.action("Center Pattern", "Meta+0", self.canvas.center_on_cells)
        self.about_action = self.action("About Conway's Game of Life", None, self.show_about)

    def _create_menus(self) -> None:
        game_menu = self.menuBar().addMenu("Game")
        game_menu.addActions((self.new_action, self.clear_action))
        game_menu.addSeparator()
        game_menu.addActions((self.run_action, self.step_action))
        game_menu.addSeparator()
        speed_menu = game_menu.addMenu("Simulation Speed")
        for label, interval in (("Slow", 500), ("Normal", DEFAULT_INTERVAL_MS), ("Fast", 65)):
            speed_action = QAction(label, self, checkable=True)
            speed_action.triggered.connect(lambda checked=False, value=interval: self.set_speed(value))
            speed_menu.addAction(speed_action)
            self.speed_actions.append(speed_action)
        self.speed_actions[1].setChecked(True)

        pattern_menu = self.menuBar().addMenu("Patterns")
        for name, cells in PATTERNS.items():
            inserted_cells = cells
            pattern_action = QAction(name, self)
            pattern_action.triggered.connect(lambda checked=False, seed=inserted_cells: self.load_pattern(seed))
            pattern_menu.addAction(pattern_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addActions((self.zoom_in_action, self.zoom_out_action, self.center_action))
        pan_menu = view_menu.addMenu("Pan")
        pan_menu.addActions((self.pan_left_action, self.pan_right_action, self.pan_up_action, self.pan_down_action))

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction(self.about_action)

    def _create_status_bar(self) -> None:
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

    def new_universe(self) -> None:
        self.pause()
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
        self.pause()
        self.universe.clear()
        self.canvas.update()
        self.update_status()

    def load_pattern(self, cells: tuple[Cell, ...]) -> None:
        self.pause()
        self.universe.set_cells(cells)
        self.canvas.center_on_cells()
        self.update_status()

    def step(self) -> None:
        self.universe.advance()
        self.canvas.update()
        self.update_status()

    def toggle_running(self) -> None:
        if self.timer.isActive():
            self.pause()
        else:
            self.timer.start()
            self.run_action.setText("Pause")
            self.run_action.setChecked(True)

    def pause(self) -> None:
        self.timer.stop()
        self.run_action.setText("Run")
        self.run_action.setChecked(False)

    def set_speed(self, interval: int) -> None:
        self.timer.setInterval(interval)
        for speed_action in self.speed_actions:
            speed_action.setChecked(speed_action.text().lower() == {500: "slow", DEFAULT_INTERVAL_MS: "normal", 65: "fast"}[interval])

    def update_status(self) -> None:
        self.status.showMessage(f"Generation: {self.universe.generation}    Population: {self.universe.population}")

    def show_about(self) -> None:
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
    configure_macos_bundle_name()
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_NAME)
    application.setOrganizationName(AUTHOR)
    icon_path = application_icon_path()
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
