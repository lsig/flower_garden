from core.point import Position
from tests.garden.garden_setup import TestGarden


class TestGardenPlantPlacement(TestGarden):
    def test_add_first_plant_successfully(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        assert plant is not None
        assert len(self.garden.plants) == 1
        assert plant.variety == self.rhodo_variety
        assert plant.position == Position(5, 5)

    def test_add_plant_outside_bounds_fails(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(20, 5))

        assert plant is None
        assert len(self.garden.plants) == 0

    def test_add_plant_with_sufficient_spacing_succeeds(self):
        # Place first plant with radius 2
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        # Place second plant with radius 2, exactly 4 meters away (min_distance = 2 + 2 = 4)
        plant2 = self.garden.add_plant(self.rhodo_variety, Position(9, 5))

        assert plant1 is not None
        assert plant2 is not None
        assert len(self.garden.plants) == 2

    def test_add_plant_with_insufficient_spacing_fails(self):
        # Place first plant with radius 2
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        # Try to place second rhodo (radius 2) too close
        # Second rhodo needs distance >= 2, but we place at distance 1.5
        plant2 = self.garden.add_plant(self.rhodo_variety, Position(6.5, 5))

        assert plant1 is not None
        assert plant2 is None  # Fails because 1.5 < 2
        assert len(self.garden.plants) == 1

    def test_add_plant_at_exact_minimum_distance_succeeds(self):
        # Radius 2 + Radius 2 = 4 minimum distance
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(0, 0))
        plant2 = self.garden.add_plant(self.rhodo_variety, Position(4, 0))

        assert plant1 is not None
        assert plant2 is not None
        assert len(self.garden.plants) == 2

    def test_add_plant_just_under_minimum_distance_fails(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(0, 0))
        # Rhodo radius = 2, so second rhodo needs distance >= 2
        plant2 = self.garden.add_plant(self.rhodo_variety, Position(1.99, 0))

        assert plant1 is not None
        assert plant2 is None  # Fails because 1.99 < 2
        assert len(self.garden.plants) == 1

    def test_add_plants_with_different_radii(self):
        # Rhodo radius = 2, Geranium radius = 1
        # Geranium only needs distance >= 1 from rhodo
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(
            self.geranium_variety, Position(6, 5)
        )  # Distance = 1

        assert plant1 is not None
        assert plant2 is not None  # Succeeds because 1 >= 1
        assert len(self.garden.plants) == 2
