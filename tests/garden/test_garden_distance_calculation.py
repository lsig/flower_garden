import math

from core.point import Position
from tests.garden.garden_setup import TestGarden


class TestGardenDistanceCalculation(TestGarden):
    def test_calculate_distance_horizontal(self):
        pos1 = Position(0, 0)
        pos2 = Position(3, 0)
        assert self.garden._calculate_distance(pos1, pos2) == 3.0

    def test_calculate_distance_vertical(self):
        pos1 = Position(0, 0)
        pos2 = Position(0, 4)
        assert self.garden._calculate_distance(pos1, pos2) == 4.0

    def test_calculate_distance_diagonal(self):
        pos1 = Position(0, 0)
        pos2 = Position(3, 4)
        assert self.garden._calculate_distance(pos1, pos2) == 5.0

    def test_calculate_distance_is_symmetric(self):
        pos1 = Position(2, 3)
        pos2 = Position(7, 9)

        dist1 = self.garden._calculate_distance(pos1, pos2)
        dist2 = self.garden._calculate_distance(pos2, pos1)

        assert dist1 == dist2

    def test_calculate_distance_with_decimals(self):
        pos1 = Position(1.5, 2.5)
        pos2 = Position(4.5, 6.5)

        expected = math.sqrt((3.0) ** 2 + (4.0) ** 2)
        assert self.garden._calculate_distance(pos1, pos2) == expected
