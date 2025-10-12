from core.micronutrients import Micronutrient
from core.point import Position
from tests.exchange.setup_exchange import TestNutrientExchange


class TestSimpleExchange(TestNutrientExchange):
    def test_exchange_between_two_plants(self):
        # Rhodo produces R, Geranium produces G
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(7, 5))

        # Set inventories
        plant1.micronutrient_inventory[Micronutrient.R] = 12.0  # Offers 3.0
        plant2.micronutrient_inventory[Micronutrient.G] = 8.0  # Offers 2.0

        initial_plant1_r = plant1.micronutrient_inventory[Micronutrient.R]
        initial_plant1_g = plant1.micronutrient_inventory[Micronutrient.G]
        initial_plant2_r = plant2.micronutrient_inventory[Micronutrient.R]
        initial_plant2_g = plant2.micronutrient_inventory[Micronutrient.G]

        # Execute exchange (minimum is 2.0)
        self.exchange.execute()

        # Verify rhodo gave R and received G
        assert plant1.micronutrient_inventory[Micronutrient.R] == initial_plant1_r - 2.0
        assert plant1.micronutrient_inventory[Micronutrient.G] == initial_plant1_g + 2.0

        # Verify geranium gave G and received R
        assert plant2.micronutrient_inventory[Micronutrient.G] == initial_plant2_g - 2.0
        assert plant2.micronutrient_inventory[Micronutrient.R] == initial_plant2_r + 2.0

    def test_exchange_uses_minimum_offer(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(7, 5))

        # Plant1 offers more than plant2
        plant1.micronutrient_inventory[Micronutrient.R] = 18.0
        plant1.micronutrient_inventory[Micronutrient.G] = 4.0

        plant2.micronutrient_inventory[Micronutrient.G] = 4.0
        plant2.micronutrient_inventory[Micronutrient.R] = 3.0

        initial_r = plant1.micronutrient_inventory[Micronutrient.R]

        self.exchange.execute()

        # Should exchange minimum (1.0)
        assert plant1.micronutrient_inventory[Micronutrient.R] == initial_r - 1.0

    def test_no_exchange_when_offer_is_zero(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(7, 5))

        # Plant1 has nothing to offer
        plant1.micronutrient_inventory[Micronutrient.R] = 0.0
        plant2.micronutrient_inventory[Micronutrient.G] = 8.0

        initial_inventories = {k: v for k, v in plant1.micronutrient_inventory.items()}

        self.exchange.execute()

        # No changes should occur
        assert plant1.micronutrient_inventory == initial_inventories

    def test_exchange_respects_reservoir_capacity(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(7, 5))

        # Plant1 at capacity for G
        plant1.micronutrient_inventory[Micronutrient.R] = 12.0
        plant1.micronutrient_inventory[Micronutrient.G] = 20.0  # At capacity

        plant2.micronutrient_inventory[Micronutrient.G] = 8.0

        self.exchange.execute()

        # Plant1's G should be capped at capacity
        assert plant1.micronutrient_inventory[Micronutrient.G] == 20.0
