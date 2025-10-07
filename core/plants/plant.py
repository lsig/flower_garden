from typing import assert_never

from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Plant:
    def __init__(self, variety: PlantVariety, position: Position) -> None:
        self.variety = variety
        self.position = position

        self.reservoir_capacity = 10 * self.variety.radius
        self.max_size = 100 * (self.variety.radius**2)

        self.size = 0.0
        self.micronutrient_inventory: dict[Micronutrient, float] = {
            nutrient: self.reservoir_capacity / 2 for nutrient in Micronutrient
        }

    def produce(self):
        if not self._can_produce():
            return

        for nutrient, coeff in self.variety.nutrient_coefficients.items():
            new_inventory = self.micronutrient_inventory[nutrient] + coeff
            self.micronutrient_inventory[nutrient] = min(
                self.reservoir_capacity, new_inventory
            )

            # NOTE: Make sure nutrients store don't go negative
            assert self.micronutrient_inventory[nutrient] >= 0

    def _can_produce(self):
        # NOTE: Should production stop if nutrient is full?
        return all(
            self.micronutrient_inventory[nutrient] + coeff >= 0
            for nutrient, coeff in self.variety.nutrient_coefficients.items()
        )

    def grow(self) -> float:
        if not self._can_grow():
            return 0.0

        for nutrient in self.micronutrient_inventory:
            self.micronutrient_inventory[nutrient] -= self.variety.radius

        self.size += self.variety.radius

        return self.variety.radius

    def _can_grow(self):
        return (
            all(
                self.micronutrient_inventory[nutrient] >= 2 * self.variety.radius
                for nutrient in self.micronutrient_inventory
            )
            and self.size < self.max_size
        )

    def offer_amount(self) -> float:
        nutrient = self._get_produced_nutrient()
        amount = self.micronutrient_inventory[nutrient] / 4
        return round(amount, 2)

    def receive_nutrient(self, nutrient: Micronutrient, amount: float) -> None:
        new_amount = self.micronutrient_inventory[nutrient] + amount
        self.micronutrient_inventory[nutrient] = min(
            self.reservoir_capacity, new_amount
        )

    def give_nutrient(self, amount: float) -> None:
        nutrient = self._get_produced_nutrient()
        self.micronutrient_inventory[nutrient] -= amount

        assert self.micronutrient_inventory[nutrient] >= 0

    def _get_produced_nutrient(self) -> Micronutrient:
        match self.variety.species:
            case Species.RHODODENDRON:
                return Micronutrient.R
            case Species.GERANIUM:
                return Micronutrient.G
            case Species.BEGONIA:
                return Micronutrient.B
            case _:
                assert_never(self.variety.species)

    def growth_percentage(self) -> float:
        return (self.size / self.max_size) * 100

    def is_fully_grown(self) -> bool:
        return self.size >= self.max_size
