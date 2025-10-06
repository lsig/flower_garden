from core.micronutrients import Micronutrient
from core.plants.plant import Plant
from core.plants.plant_dto import PlantDTO
from core.plants.species import Species


class TestPlantGrowth:
    def setup_method(self, method):
        test_variety = PlantDTO(
            name="Test Geranium",
            radius=2,
            species=Species.GERANIUM,
            nutrient_coefficents={
                Micronutrient.R: -1.0,
                Micronutrient.G: 4.0,
                Micronutrient.B: -1.0,
            },
        )
        self.plant = Plant(variety=test_variety, position=(0, 0))

    def test_can_grow_when_sufficient_nutrients_and_not_max_size(self):
        self.plant.size = 50
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 10.0,
            Micronutrient.G: 10.0,
            Micronutrient.B: 10.0,
        }

        assert self.plant._can_grow() is True

        self.plant.grow()

        assert self.plant.size == 52
        assert self.plant.micronutrient_inventory == {
            Micronutrient.R: 8.0,
            Micronutrient.G: 8.0,
            Micronutrient.B: 8.0,
        }

    def test_cannot_grow_when_nutrients_are_insufficient(self):
        self.plant.size = 50
        initial_inventory = {
            Micronutrient.R: 10.0,
            Micronutrient.G: 3.9,
            Micronutrient.B: 10.0,
        }
        self.plant.micronutrient_inventory = initial_inventory.copy()

        assert self.plant._can_grow() is False

        self.plant.grow()

        assert self.plant.size == 50
        assert self.plant.micronutrient_inventory == initial_inventory

    def test_cannot_grow_when_at_max_size(self):
        self.plant.size = self.plant.max_size
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 10.0,
            Micronutrient.G: 10.0,
            Micronutrient.B: 10.0,
        }

        assert self.plant._can_grow() is False

        self.plant.grow()

        assert self.plant.size == self.plant.max_size

    def test_can_grow_at_exact_nutrient_boundary(self):
        self.plant.size = 50
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 4.0,
            Micronutrient.G: 4.0,
            Micronutrient.B: 4.0,
        }

        assert self.plant._can_grow() is True

        self.plant.grow()

        assert self.plant.size == 52
        assert self.plant.micronutrient_inventory == {
            Micronutrient.R: 2.0,
            Micronutrient.G: 2.0,
            Micronutrient.B: 2.0,
        }

    def test_grow_stops_exactly_at_max_size(self):
        self.plant.size = self.plant.max_size - self.plant.variety.radius
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 10.0,
            Micronutrient.G: 10.0,
            Micronutrient.B: 10.0,
        }

        self.plant.grow()
        assert self.plant.size == self.plant.max_size

        self.plant.grow()
        assert self.plant.size == self.plant.max_size
