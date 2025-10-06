from core.micronutrients import Micronutrient
from core.plants.plant import Plant
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species


class TestPlantExchange:
    def setup_method(self, method):
        rhodo_variety = PlantVariety(
            name="Test Rhododendron",
            radius=2,
            species=Species.RHODODENDRON,
            nutrient_coefficients={
                Micronutrient.R: 3.0,
                Micronutrient.G: -1.0,
                Micronutrient.B: -1.0,
            },
        )
        self.rhodo = Plant(variety=rhodo_variety, position=(0, 0))

        geranium_variety = PlantVariety(
            name="Test Geranium",
            radius=2,
            species=Species.GERANIUM,
            nutrient_coefficients={
                Micronutrient.R: -1.0,
                Micronutrient.G: 4.0,
                Micronutrient.B: -1.0,
            },
        )
        self.geranium = Plant(variety=geranium_variety, position=(5, 5))

        begonia_variety = PlantVariety(
            name="Test Begonia",
            radius=2,
            species=Species.BEGONIA,
            nutrient_coefficients={
                Micronutrient.R: -1.0,
                Micronutrient.G: -1.0,
                Micronutrient.B: 3.0,
            },
        )
        self.begonia = Plant(variety=begonia_variety, position=(10, 10))

    def test_offer_amount_is_one_quarter_of_inventory(self):
        self.rhodo.micronutrient_inventory[Micronutrient.R] = 12.0
        assert self.rhodo.offer_amount() == 3.0

        self.geranium.micronutrient_inventory[Micronutrient.G] = 8.0
        assert self.geranium.offer_amount() == 2.0

    def test_offer_amount_rounds_to_two_decimals(self):
        self.rhodo.micronutrient_inventory[Micronutrient.R] = 10.0
        assert self.rhodo.offer_amount() == 2.5

        self.rhodo.micronutrient_inventory[Micronutrient.R] = 10.13
        assert self.rhodo.offer_amount() == 2.53

    def test_give_nutrient_decreases_produced_nutrient(self):
        self.rhodo.micronutrient_inventory[Micronutrient.R] = 12.0
        self.rhodo.give_nutrient(3.0)
        assert self.rhodo.micronutrient_inventory[Micronutrient.R] == 9.0

    def test_give_nutrient_only_affects_produced_nutrient(self):
        initial_g = self.rhodo.micronutrient_inventory[Micronutrient.G]
        initial_b = self.rhodo.micronutrient_inventory[Micronutrient.B]

        self.rhodo.micronutrient_inventory[Micronutrient.R] = 12.0
        self.rhodo.give_nutrient(3.0)

        assert self.rhodo.micronutrient_inventory[Micronutrient.G] == initial_g
        assert self.rhodo.micronutrient_inventory[Micronutrient.B] == initial_b

    def test_give_nutrient_at_exact_zero_boundary(self):
        self.rhodo.micronutrient_inventory[Micronutrient.R] = 3.0
        self.rhodo.give_nutrient(3.0)
        assert self.rhodo.micronutrient_inventory[Micronutrient.R] == 0.0

    def test_receive_nutrient_increases_specified_nutrient(self):
        initial_g = self.rhodo.micronutrient_inventory[Micronutrient.G]
        self.rhodo.receive_nutrient(Micronutrient.G, 2.0)

        assert self.rhodo.micronutrient_inventory[Micronutrient.G] == initial_g + 2.0

    def test_receive_nutrient_does_not_affect_other_nutrients(self):
        initial_r = self.rhodo.micronutrient_inventory[Micronutrient.R]
        initial_b = self.rhodo.micronutrient_inventory[Micronutrient.B]

        self.rhodo.receive_nutrient(Micronutrient.G, 2.0)

        assert self.rhodo.micronutrient_inventory[Micronutrient.R] == initial_r
        assert self.rhodo.micronutrient_inventory[Micronutrient.B] == initial_b

    def test_receive_nutrient_respects_reservoir_capacity(self):
        self.rhodo.micronutrient_inventory[Micronutrient.G] = 19.0
        self.rhodo.receive_nutrient(Micronutrient.G, 5.0)

        assert self.rhodo.micronutrient_inventory[Micronutrient.G] == 20.0

    def test_receive_nutrient_can_receive_any_nutrient_type(self):
        initial_r = self.rhodo.micronutrient_inventory[Micronutrient.R]
        initial_g = self.rhodo.micronutrient_inventory[Micronutrient.G]
        initial_b = self.rhodo.micronutrient_inventory[Micronutrient.B]

        self.rhodo.receive_nutrient(Micronutrient.R, 1.0)
        self.rhodo.receive_nutrient(Micronutrient.G, 2.0)
        self.rhodo.receive_nutrient(Micronutrient.B, 3.0)

        assert self.rhodo.micronutrient_inventory[Micronutrient.R] == min(
            initial_r + 1.0, 20.0
        )
        assert self.rhodo.micronutrient_inventory[Micronutrient.G] == min(
            initial_g + 2.0, 20.0
        )
        assert self.rhodo.micronutrient_inventory[Micronutrient.B] == min(
            initial_b + 3.0, 20.0
        )

    def test_different_species_produce_different_nutrients(self):
        assert self.rhodo._get_produced_nutrient() == Micronutrient.R
        assert self.geranium._get_produced_nutrient() == Micronutrient.G
        assert self.begonia._get_produced_nutrient() == Micronutrient.B
