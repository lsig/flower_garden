from core.micronutrients import Micronutrient
from core.plants.plant_dto import PlantDTO
from core.point import Position


class Plant:
    def __init__(self, variety: PlantDTO, position: Position) -> None:
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

        for nutrient, coeff in self.variety.nutrient_coefficents.items():
            self.micronutrient_inventory[nutrient] += coeff

    def exchange(self):
        pass

    def grow(self):
        pass

    def _can_produce(self):
        return all(
            self.micronutrient_inventory[nutrient] + coeff >= 0
            for nutrient, coeff in self.variety.nutrient_coefficents.items()
        )
