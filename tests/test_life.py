"""Unit tests for the pure Life rule engine."""

from gameoflife.life import LifeUniverse, cells_on_line


def test_cells_on_line_includes_every_cell_between_endpoints() -> None:
    """Verify that a horizontal stroke includes each intervening cell."""
    assert cells_on_line((0, 0), (3, 0)) == ((0, 0), (1, 0), (2, 0), (3, 0))


def test_cells_on_line_supports_diagonal_strokes_in_either_direction() -> None:
    """Verify that a reverse diagonal stroke includes every crossed cell."""
    assert cells_on_line((2, 2), (-1, -1)) == ((2, 2), (1, 1), (0, 0), (-1, -1))


def test_underpopulation_kills_a_lone_cell() -> None:
    """Verify that a live cell without neighbours dies."""
    universe: LifeUniverse = LifeUniverse({(0, 0)})

    universe.advance()

    assert universe.live_cells == set()
    assert universe.generation == 1


def test_blinker_oscillates() -> None:
    """Verify that the period-two blinker alternates as expected."""
    universe: LifeUniverse = LifeUniverse({(-1, 0), (0, 0), (1, 0)})

    universe.advance()

    assert universe.live_cells == {(0, -1), (0, 0), (0, 1)}
    universe.advance()
    assert universe.live_cells == {(-1, 0), (0, 0), (1, 0)}


def test_block_is_a_still_life() -> None:
    """Verify that a block remains unchanged after one generation."""
    cells: set[tuple[int, int]] = {(0, 0), (1, 0), (0, 1), (1, 1)}
    universe: LifeUniverse = LifeUniverse(cells)

    universe.advance()

    assert universe.live_cells == cells


def test_exactly_three_neighbours_creates_a_cell() -> None:
    """Verify that a dead cell is born when it has three neighbours."""
    universe: LifeUniverse = LifeUniverse({(-1, 0), (0, 0), (1, 0)})

    universe.advance()

    assert (0, -1) in universe.live_cells
    assert (0, 1) in universe.live_cells
