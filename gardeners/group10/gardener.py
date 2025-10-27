from typing import Optional
from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety

from gardeners.group10.greedy_algorithm_with_replacement_1027.gardener import GreedyGardener


class Gardener10(Gardener):
    """
    Group 10's Gardener implementation using Greedy Planting Algorithm.

    This gardener uses an optimized greedy algorithm with:
    - Fixed center-point initialization for first plant
    - Horizontal right placement for second plant
    - Multi-species interaction zones (hard constraint from 3rd plant onwards)
    - Radius-descending order for first 3 plants
    - Nutrient-balanced variety prioritization
    - Simulation-based scoring with short/long-term growth weighting
    - Pattern replication for efficient space utilization
    """

    def __init__(
        self, garden: Garden, varieties: list[PlantVariety], simulation_turns: Optional[int] = None
    ):
        """
        Initialize Gardener10.

        Args:
            garden: Garden to place plants in
            varieties: List of available plant varieties
            simulation_turns: Optional number of simulation turns for scoring.
                            If not provided, uses default from config.yaml (T=100)
        """
        super().__init__(garden, varieties)
        # Delegate to the greedy algorithm implementation with simulation_turns
        self._greedy_gardener = GreedyGardener(garden, varieties, simulation_turns=simulation_turns)

    def cultivate_garden(self) -> None:
        """Place plants using the greedy planting algorithm."""
        self._greedy_gardener.cultivate_garden()
