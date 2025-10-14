from core.garden import Garden
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species


class TestGarden:
    def setup_method(self, method):
        self.garden = Garden(width=16, height=10)

        self.rhodo_variety = PlantVariety(
            name='Test Rhododendron',
            radius=2,
            species=Species.RHODODENDRON,
            nutrient_coefficients={
                Micronutrient.R: 3.0,
                Micronutrient.G: -1.0,
                Micronutrient.B: -1.0,
            },
        )

        self.geranium_variety = PlantVariety(
            name='Test Geranium',
            radius=1,
            species=Species.GERANIUM,
            nutrient_coefficients={
                Micronutrient.R: -0.5,
                Micronutrient.G: 2.0,
                Micronutrient.B: -0.5,
            },
        )

        self.begonia_variety = PlantVariety(
            name='Test Begonia',
            radius=3,
            species=Species.BEGONIA,
            nutrient_coefficients={
                Micronutrient.R: -1.0,
                Micronutrient.G: -1.0,
                Micronutrient.B: 4.0,
            },
        )
