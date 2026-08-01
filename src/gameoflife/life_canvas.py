from typing import Final

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QShowEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from gameoflife.life import Cell, LifeUniverse, cells_on_line

ANIMATION_FRAME_INTERVAL_MS: Final[int] = 16
BACKGROUND_COLOR: Final[QColor] = QColor("#000000")
GRID_COLOR: Final[QColor] = QColor(90, 90, 90, 115)
MIN_CELL_SIZE: Final[float] = 4.0
MAX_CELL_SIZE: Final[float] = 64.0
PAN_INCREMENT_CELLS: Final[int] = 4
ZOOM_MULTIPLIER: Final[float] = 1.18
WHEEL_ZOOM_MULTIPLIER: Final[float] = 1.02

class LifeCanvas(QWidget):
    """Pannable, zoomable viewport over a sparse infinite Life universe."""

    changed: Signal = Signal()

    def __init__(self,
                 universe: LifeUniverse,
                 cell_size: float,
                 parent: QWidget | None = None) -> None:
        """Create a canvas that displays and edits a Life universe."""
        super().__init__(parent)
        self.universe: LifeUniverse = universe
        self.cell_size: float = cell_size
        self.origin: QPointF = QPointF()
        self._last_drag_position: QPointF | None = None
        self._last_toggled_cell: Cell | None = None
        self._drag_button: Qt.MouseButton | None = None
        self._dragging: bool = False
        self._toggled_cells: set[Cell] = set()
        self._birth_cells: set[Cell] = set()
        self._death_cells: set[Cell] = set()
        self._transition_clock: QElapsedTimer = QElapsedTimer()
        self._animation_timer: QTimer = QTimer(self)
        self._animation_timer.setInterval(ANIMATION_FRAME_INTERVAL_MS)
        self._animation_timer.timeout.connect(self._advance_transition)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def showEvent(self, event: QShowEvent) -> None:
        """Center the empty universe when the canvas first becomes visible."""
        super().showEvent(event)
        if self.origin.isNull():
            self.origin = QPointF(self.width() / 2,
            self.height() / 2)

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
        average_column: float = sum(cell[0]
                                    for cell in self.universe.live_cells) / self.universe.population
        average_row: float = sum(cell[1]
                                 for cell in self.universe.live_cells) / self.universe.population
        self.origin = QPointF(
            self.width() / 2 - average_column * self.cell_size,
            self.height() / 2 - average_row * self.cell_size,
        )
        self.update()

    def zoom_in(self) -> None:
        """Zoom in on the canvas."""
        self.zoom(ZOOM_MULTIPLIER)

    def zoom_out(self) -> None:
        """Zoom out of the canvas."""
        self.zoom(1 / ZOOM_MULTIPLIER)

    def zoom(self, multiplier: float, focus: QPointF | None = None) -> None:
        """Scale the viewport around an optional focus point."""
        focus_point: QPointF = focus or QPointF(self.width() / 2,
                                                self.height() / 2)
        old_size: float = self.cell_size
        new_size: float = max(MIN_CELL_SIZE,
                              min(MAX_CELL_SIZE,
                                  old_size * multiplier))
        if new_size == old_size:
            return
        cell_x: float = (focus_point.x() - self.origin.x()) / old_size
        cell_y: float = (focus_point.y() - self.origin.y()) / old_size
        self.cell_size = new_size
        self.origin = QPointF(focus_point.x() - cell_x * new_size,
                              focus_point.y() - cell_y * new_size)
        self.update()

    def pan_by_cells(self, column_direction: int, row_direction: int) -> None:
        """Move the viewport by a fixed number of cells.
        negative values move left or up, positive values move right or down, zero does not move."""
        column_offset: float = column_direction * PAN_INCREMENT_CELLS * self.cell_size
        row_offset: float = row_direction * PAN_INCREMENT_CELLS * self.cell_size
        self.origin -= QPointF(column_offset, row_offset)
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
        self.transition_duration_ms = max(1, duration_ms)
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
        return min(1.0,
                   elapsed_ms / self.transition_duration_ms)

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
        if not base_rectangle.intersects(QRectF(self.rect())):
            return
        visible_width: float = base_rectangle.width() * min(1.0,
                                                            facing_scale)
        visible_left: float = base_rectangle.center().x() - visible_width / 2
        visible_rectangle: QRectF = QRectF(
            visible_left,
            base_rectangle.top(),
            visible_width,
            base_rectangle.height(),
        )
        cell_color: QColor = QColor(color)
        cell_color.setAlphaF(min(1.0,
                                 opacity))
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
                painter.drawLine(QPointF(x, 0),
                                 QPointF(x, self.height()))
            for row in range(start_row, end_row + 1):
                y: float = self.origin.y() + row * self.cell_size
                painter.drawLine(QPointF(0, y),
                                 QPointF(self.width(), y))

        live_color: QColor = self.palette().highlight().color()
        painter.setPen(Qt.PenStyle.NoPen)
        transition_progress: float = self._transition_progress()
        stable_cells: set[Cell] = self.universe.live_cells - self._birth_cells
        for cell in stable_cells:
            self._draw_cell(painter,
                            cell,
                            live_color)
        for cell in self._birth_cells:
            self._draw_cell(painter,
                            cell,
                            live_color,
                            transition_progress,
                            transition_progress)
        death_scale: float = 1.0 - transition_progress
        for cell in self._death_cells:
            self._draw_cell(painter,
                            cell,
                            live_color,
                            death_scale,
                            death_scale)

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
        if event.angleDelta().y() > 0:
            self.zoom(WHEEL_ZOOM_MULTIPLIER, event.position())
        else:
            self.zoom(1 / WHEEL_ZOOM_MULTIPLIER, event.position())
