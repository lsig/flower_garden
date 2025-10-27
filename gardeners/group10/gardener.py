from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from gardeners.group10.greedy_planting_algorithm_1026.gardener import GreedyGardener


class Gardener10(Gardener):
    """
    Group 10's Gardener implementation using Greedy Planting Algorithm.

    This gardener uses an optimized greedy algorithm with:
    - Fixed center-point initialization for first plant
    - Multi-species interaction zones (hard constraint from 3rd plant onwards)
    - Nutrient-balanced variety prioritization
    - Simulation-based scoring with short/long-term growth weighting
    """

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        # Delegate to the greedy algorithm implementation
        self._greedy_gardener = GreedyGardener(garden, varieties)

    def cultivate_garden(self) -> None:
        """Place plants using the greedy planting algorithm."""
        self._greedy_gardener.cultivate_garden()
