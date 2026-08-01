"""The rule engine for Conway's Game of Life (B3/S23)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import TypeAlias

Cell: TypeAlias = tuple[int, int]
"""A grid cell in Conway's Game of Life, represented as (column, row)."""

def cells_on_line(start: Cell, end: Cell) -> tuple[Cell, ...]:
    """Return each grid cell crossed by a straight, integer-cell stroke."""
    column: int
    row: int
    column, row = start
    end_column: int
    end_row: int
    end_column, end_row = end
    cells: list[Cell] = []
    column_delta: int = abs(end_column - column)
    row_delta: int = -abs(end_row - row)
    column_step: int = 1 if column < end_column else -1
    row_step: int = 1 if row < end_row else -1
    error: int = column_delta + row_delta

    while True:
        cells.append((column, row))
        if (column, row) == end:
            return tuple(cells)
        doubled_error: int = 2 * error
        if doubled_error >= row_delta:
            error += row_delta
            column += column_step
        if doubled_error <= column_delta:
            error += column_delta
            row += row_step


class LifeUniverse:
    """An unbounded, sparse Conway's Game of Life universe."""

    def __init__(self, live_cells: Iterable[Cell] = ()) -> None:
        """Initialize the universe with an optional collection of live cells."""
        self.live_cells: set[Cell] = set(live_cells)
        self.generation: int = 0

    @property
    def population(self) -> int:
        """Return the number of currently live cells."""
        return len(self.live_cells)

    def clear(self) -> None:
        """Remove every live cell and reset the generation count."""
        self.live_cells.clear()
        self.generation = 0

    def set_cells(self, cells: Iterable[Cell]) -> None:
        """Replace the universe with cells and reset the generation count."""
        self.live_cells = set(cells)
        self.generation = 0

    def toggle(self, cell: Cell) -> None:
        """Invert the state of one cell without advancing the universe."""
        if cell in self.live_cells:
            self.live_cells.remove(cell)
        else:
            self.live_cells.add(cell)

    def advance(self) -> None:
        """Apply B3/S23 once, simultaneously, to all relevant cells."""

        # For each cell, add one to each neighbor's count
        neighbors: Counter[Cell] = Counter()
        for column, row in self.live_cells:
            for delta_column in (-1, 0, 1):
                for delta_row in (-1, 0, 1):
                    if delta_column != 0 or delta_row != 0:
                        neighbors[(column + delta_column, row + delta_row)] += 1

        # set comprehension: consise expression to generate a set collection
        # generate a set of live_cells with 3 neighbors, or 2 neighbors if already alive
        self.live_cells = {
            cell
            for cell, count in neighbors.items()
            if count == 3 or (count == 2 and cell in self.live_cells)
        }
        self.generation += 1
