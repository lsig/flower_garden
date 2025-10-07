from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety


class Gardener4(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        pass
