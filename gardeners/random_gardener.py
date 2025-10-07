import random

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position


class RandomGardener(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        for variety in self.varieties:
            x = random.uniform(0, self.garden.width)
            y = random.uniform(0, self.garden.height)

            position = Position(x, y)

            self.garden.add_plant(variety, position)
