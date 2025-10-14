from core.garden import Garden
from core.plants.plant import Plant


class NutrientExchange:
    def __init__(self, garden: Garden) -> None:
        self.garden = garden
        self.offers = {}

    def _calculate_offer_to_partner(self, plant: Plant) -> float:
        total_offer = plant.offer_amount()
        partners = self.garden.get_interacting_plants(plant)

        num_partners = len(partners)
        return total_offer / num_partners if num_partners > 0 else 0.0

    def _should_exchange(self, plant1: Plant, plant2: Plant) -> bool:
        nutrient1 = plant1._get_produced_nutrient()
        nutrient2 = plant2._get_produced_nutrient()

        plant1_has_surplus = (
            plant1.micronutrient_inventory[nutrient1] > plant1.micronutrient_inventory[nutrient2]
        )

        plant2_has_surplus = (
            plant2.micronutrient_inventory[nutrient2] > plant2.micronutrient_inventory[nutrient1]
        )

        return plant1_has_surplus and plant2_has_surplus

    def _exchange_nutrients(self, plant1: Plant, plant2: Plant) -> None:
        offer1 = self.offers[id(plant1)]
        offer2 = self.offers[id(plant2)]

        exchange_amount = min(offer1, offer2)

        if exchange_amount > 0:
            nutrient1 = plant1._get_produced_nutrient()
            nutrient2 = plant2._get_produced_nutrient()

            plant1.give_nutrient(exchange_amount)
            plant1.receive_nutrient(nutrient2, exchange_amount)

            plant2.give_nutrient(exchange_amount)
            plant2.receive_nutrient(nutrient1, exchange_amount)

    def execute(self) -> None:
        interactions = self.garden.get_all_interactions()
        eligible_exchanges = []

        for plant in self.garden.plants:
            self.offers[id(plant)] = self._calculate_offer_to_partner(plant)

        for plant1, plant2 in interactions:
            if self._should_exchange(plant1, plant2):
                eligible_exchanges.append((plant1, plant2))

        for plant1, plant2 in eligible_exchanges:
            self._exchange_nutrients(plant1, plant2)
