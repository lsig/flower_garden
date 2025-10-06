from core.point import Position
from tests.garden.garden_setup import TestGarden


class TestGardenGrowthTracking(TestGarden):
    def test_total_growth_empty_garden(self):
        assert self.garden.total_growth() == 0.0

    def test_total_growth_initial_plants(self):
        _plant1 = self.garden.add_plant(self.rhodo_variety, Position(2, 2))
        _plant2 = self.garden.add_plant(self.rhodo_variety, Position(10, 2))

        assert self.garden.total_growth() == 0.0

    def test_total_growth_after_growth(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(2, 2))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(10, 2))

        plant1.size = 50.0
        plant2.size = 30.0

        assert self.garden.total_growth() == 80.0

    def test_total_growth_updates_dynamically(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        assert self.garden.total_growth() == 0.0

        plant.size = 25.0
        assert self.garden.total_growth() == 25.0

        plant.size = 100.0
        assert self.garden.total_growth() == 100.0
