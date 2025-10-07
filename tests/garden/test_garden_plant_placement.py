from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
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

        # Place second plant with radius 3, exactly 5 meters away
        plant2 = self.garden.add_plant(self.begonia_variety, Position(10, 5))

        assert plant1 is not None
        assert plant2 is not None
        assert len(self.garden.plants) == 2

    def test_add_plant_with_insufficient_spacing_fails(self):
        # Place first plant with radius 2
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        plant2 = self.garden.add_plant(self.begonia_variety, Position(6.5, 5))

        assert plant1 is not None
        assert plant2 is None  # Fails because 1.5 < 3
        assert len(self.garden.plants) == 1

    def test_add_plant_at_exact_minimum_distance_succeeds(self):
        # minimum distance radii 3
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(0, 0))
        plant2 = self.garden.add_plant(self.begonia_variety, Position(3, 0))

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

    def test_cannot_plant_same_variety_instance_twice(self):
        # Place a plant successfully
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        assert plant1 is not None
        assert len(self.garden.plants) == 1

        # Try to place the same variety instance again at a different location
        plant2 = self.garden.add_plant(self.rhodo_variety, Position(10, 5))

        # Should fail because the variety was already used
        assert plant2 is None
        assert len(self.garden.plants) == 1  # Still only one plant

    def test_can_plant_different_instances_of_same_variety_type(self):
        # Create two separate instances with identical values
        variety1 = PlantVariety(
            name="Rhodo A",
            radius=2,
            species=Species.RHODODENDRON,
            nutrient_coefficients={
                Micronutrient.R: 3.0,
                Micronutrient.G: -1.0,
                Micronutrient.B: -1.0,
            },
        )

        variety2 = PlantVariety(
            name="Rhodo A",
            radius=2,
            species=Species.RHODODENDRON,
            nutrient_coefficients={
                Micronutrient.R: 3.0,
                Micronutrient.G: -1.0,
                Micronutrient.B: -1.0,
            },
        )

        # These are different objects even though they have the same values
        assert id(variety1) != id(variety2)

        # Both should be placeable
        plant1 = self.garden.add_plant(variety1, Position(5, 5))
        plant2 = self.garden.add_plant(variety2, Position(10, 5))

        assert plant1 is not None
        assert plant2 is not None
        assert len(self.garden.plants) == 2
