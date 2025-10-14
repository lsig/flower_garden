from core.micronutrients import Micronutrient
from core.plants.plant import Plant
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species


class TestPlantProduction:
    def setup_method(self, method):
        test_variety = PlantVariety(
            name='Test Rhodo',
            radius=1,
            species=Species.RHODODENDRON,
            nutrient_coefficients={
                Micronutrient.R: 2.0,
                Micronutrient.G: -0.5,
                Micronutrient.B: -0.5,
            },
        )
        self.plant = Plant(variety=test_variety, position=(0, 0))

    def test_can_produce_when_sufficient_nutrients(self):
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 5,
            Micronutrient.G: 5,
            Micronutrient.B: 5,
        }

        assert self.plant._can_produce() is True

        self.plant.produce()

        assert self.plant.micronutrient_inventory == {
            Micronutrient.R: 7.0,
            Micronutrient.G: 4.5,
            Micronutrient.B: 4.5,
        }

    def test_cannot_produce_when_one_nutrient_is_insufficient(self):
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 5,
            Micronutrient.G: 0.2,
            Micronutrient.B: 5,
        }
        inital_inventory = self.plant.micronutrient_inventory.copy()

        assert self.plant._can_produce() is False

        self.plant.produce()

        assert self.plant.micronutrient_inventory == inital_inventory

    def test_can_produce_at_exact_zero_boundary(self):
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 5,
            Micronutrient.G: 0.5,
            Micronutrient.B: 5,
        }

        assert self.plant._can_produce() is True

        self.plant.produce()

        assert self.plant.micronutrient_inventory == {
            Micronutrient.R: 7.0,
            Micronutrient.G: 0.0,
            Micronutrient.B: 4.5,
        }

    def test_cant_produce_more_than_max(self):
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 8.5,
            Micronutrient.G: 0.5,
            Micronutrient.B: 5,
        }

        assert self.plant._can_produce() is True

        self.plant.produce()

        assert self.plant.micronutrient_inventory == {
            Micronutrient.R: 10.0,
            Micronutrient.G: 0.0,
            Micronutrient.B: 4.5,
        }

    def test_inventory_lowers_at_max_capacity(self):
        self.plant.micronutrient_inventory = {
            Micronutrient.R: 10.0,
            Micronutrient.G: 0.5,
            Micronutrient.B: 5,
        }

        assert self.plant._can_produce() is True

        self.plant.produce()

        assert self.plant.micronutrient_inventory == {
            Micronutrient.R: 10.0,
            Micronutrient.G: 0.0,
            Micronutrient.B: 4.5,
        }
