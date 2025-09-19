from core.micronutrients import Micronutrient
from core.plants.plant import Plant
from core.plants.plant_dto import PlantDTO
from core.plants.species import Species


class TestPlantProduction:
    def setup_method(self, method):
        test_variety = PlantDTO(
            name="Test Rhodo",
            radius=1,
            species=Species.RHODODENDRON,
            nutrient_coefficents={
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

        assert self.plant._can_produce() is False

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
