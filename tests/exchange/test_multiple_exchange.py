from core.micronutrients import Micronutrient
from core.point import Position
from tests.exchange.setup_exchange import TestNutrientExchange


class TestMultipleExchanges(TestNutrientExchange):
    def test_execute_processes_all_interactions(self):
        # Create three plants that can all interact
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))
        plant3 = self.garden.add_plant(
            self.begonia_variety, Position(5, 9)
        )  # Far enough away

        # Verify all plants were placed
        assert plant1 is not None
        assert plant2 is not None
        assert plant3 is not None

        # Set inventories
        plant1.micronutrient_inventory[Micronutrient.R] = 12.0
        plant2.micronutrient_inventory[Micronutrient.G] = 12.0
        plant3.micronutrient_inventory[Micronutrient.B] = 12.0

        self.exchange.execute()

        # All plants should have exchanged
        assert plant1.micronutrient_inventory[Micronutrient.R] < 12.0
        assert plant2.micronutrient_inventory[Micronutrient.G] < 12.0
        assert plant3.micronutrient_inventory[Micronutrient.B] < 12.0

    def test_plant_with_two_partners_splits_offer(self):
        # Rhodo in center, with Geranium and Begonia close enough to interact
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))
        plant3 = self.garden.add_plant(self.begonia_variety, Position(5, 9))

        assert plant1 is not None
        assert plant2 is not None
        assert plant3 is not None

        partners1 = self.garden.get_interacting_plants(plant1)
        partners2 = self.garden.get_interacting_plants(plant2)
        partners3 = self.garden.get_interacting_plants(plant3)

        print(f"Plant1 partners: {len(partners1)}")
        print(f"Plant2 partners: {len(partners2)}")
        print(f"Plant3 partners: {len(partners3)}")

        # Verify plant1 actually has 2 partners
        partners = self.garden.get_interacting_plants(plant1)
        assert len(partners) == 2

        plant1.micronutrient_inventory[Micronutrient.R] = 16.0  # Offers 4.0 total
        plant2.micronutrient_inventory[Micronutrient.G] = 12.0  # Offers 3.0
        plant3.micronutrient_inventory[Micronutrient.B] = 12.0  # Offers 3.0

        initial_r = plant1.micronutrient_inventory[Micronutrient.R]

        self.exchange.execute()

        # Rhodo offers 4.0 split between 2 partners = 2.0 each
        # Both partners offer 3.0 (no splitting needed)
        # So minimum is 2.0 for both exchanges
        expected_r_remaining = initial_r - 2.0 - 2.0
        assert plant1.micronutrient_inventory[Micronutrient.R] == expected_r_remaining
