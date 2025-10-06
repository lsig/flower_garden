from core.micronutrients import Micronutrient
from core.point import Position
from tests.exchange.setup_exchange import TestNutrientExchange


class TestOfferCalculations(TestNutrientExchange):
    def test_offer_with_single_partner(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        # Set R inventory to 12 for rhodo
        plant1.micronutrient_inventory[Micronutrient.R] = 12.0

        # Rhodo offers 12/4 = 3.0 total, with 1 partner = 3.0 per partner
        offer = self.exchange._calculate_offer_to_partner(plant1)
        assert offer == 3.0

    def test_offer_split_among_multiple_partners(self):
        # Place rhodo with two different species nearby
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))
        plant3 = self.garden.add_plant(self.begonia_variety, Position(6, 8))

        # Set R inventory to 12 for rhodo
        plant1.micronutrient_inventory[Micronutrient.R] = 12.0

        # Rhodo offers 12/4 = 3.0 total, split between 2 partners = 1.5 each
        offer_to_plant2 = self.exchange._calculate_offer_to_partner(plant1)
        offer_to_plant3 = self.exchange._calculate_offer_to_partner(plant1)

        assert offer_to_plant2 == 1.5
        assert offer_to_plant3 == 1.5

    def test_offer_with_no_partners(self):
        # Plant with no interactions
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(15, 5))

        plant1.micronutrient_inventory[Micronutrient.R] = 12.0

        offer = self.exchange._calculate_offer_to_partner(plant1)
        assert offer == 0.0
