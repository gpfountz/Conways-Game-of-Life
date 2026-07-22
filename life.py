"""The rule engine for Conway's Game of Life (B3/S23)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

Cell = tuple[int, int]


class LifeUniverse:
    """An unbounded, sparse Conway's Game of Life universe."""

    def __init__(self, live_cells: Iterable[Cell] = ()) -> None:
        self.live_cells: set[Cell] = set(live_cells)
        self.generation: int = 0

    @property
    def population(self) -> int:
        return len(self.live_cells)

    def clear(self) -> None:
        self.live_cells.clear()
        self.generation = 0

    def set_cells(self, cells: Iterable[Cell]) -> None:
        self.live_cells = set(cells)
        self.generation = 0

    def toggle(self, cell: Cell) -> None:
        if cell in self.live_cells:
            self.live_cells.remove(cell)
        else:
            self.live_cells.add(cell)

    def advance(self) -> None:
        """Apply B3/S23 once, simultaneously, to all relevant cells."""
        neighbors: Counter[Cell] = Counter()
        for column, row in self.live_cells:
            for delta_column in (-1, 0, 1):
                for delta_row in (-1, 0, 1):
                    if delta_column != 0 or delta_row != 0:
                        neighbors[(column + delta_column, row + delta_row)] += 1

        self.live_cells = {
            cell
            for cell, count in neighbors.items()
            if count == 3 or (count == 2 and cell in self.live_cells)
        }
        self.generation += 1
