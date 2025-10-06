from core.point import Position
from tests.garden.garden_setup import TestGarden


class TestGardenBounds(TestGarden):
    def test_position_within_bounds(self):
        assert self.garden.within_bounds(Position(0, 0)) is True
        assert self.garden.within_bounds(Position(8, 5)) is True
        assert self.garden.within_bounds(Position(16, 10)) is True

    def test_position_outside_bounds(self):
        assert self.garden.within_bounds(Position(-1, 5)) is False
        assert self.garden.within_bounds(Position(5, -1)) is False
        assert self.garden.within_bounds(Position(17, 5)) is False
        assert self.garden.within_bounds(Position(5, 11)) is False

    def test_position_at_boundary(self):
        assert self.garden.within_bounds(Position(0, 0)) is True
        assert self.garden.within_bounds(Position(16, 0)) is True
        assert self.garden.within_bounds(Position(0, 10)) is True
        assert self.garden.within_bounds(Position(16, 10)) is True
