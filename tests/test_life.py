"""Unit tests for the pure Life rule engine."""

from life import LifeUniverse


def test_underpopulation_kills_a_lone_cell() -> None:
    universe = LifeUniverse({(0, 0)})

    universe.advance()

    assert universe.live_cells == set()
    assert universe.generation == 1


def test_blinker_oscillates() -> None:
    universe = LifeUniverse({(-1, 0), (0, 0), (1, 0)})

    universe.advance()

    assert universe.live_cells == {(0, -1), (0, 0), (0, 1)}
    universe.advance()
    assert universe.live_cells == {(-1, 0), (0, 0), (1, 0)}


def test_block_is_a_still_life() -> None:
    cells = {(0, 0), (1, 0), (0, 1), (1, 1)}
    universe = LifeUniverse(cells)

    universe.advance()

    assert universe.live_cells == cells


def test_exactly_three_neighbours_creates_a_cell() -> None:
    universe = LifeUniverse({(-1, 0), (0, 0), (1, 0)})

    universe.advance()

    assert (0, -1) in universe.live_cells
    assert (0, 1) in universe.live_cells
