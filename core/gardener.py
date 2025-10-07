from abc import ABC, abstractmethod

from core.garden import Garden
from core.plants.plant_variety import PlantVariety


class Gardener(ABC):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        self.garden = garden
        self.varieties = varieties

    @abstractmethod
    def cultivate_garden(self) -> None:
        """
        Place plants in the garden using self.garden.add_plant().

        This method must complete within the time limit (default 60 seconds).

        The garden will validate placement and reject invalid positions.
        """
        pass
