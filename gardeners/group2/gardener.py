# Assuming this import works based on your file structure
from .greedygardener import GreedyVersion1 
from .balance import BalancerGreedy

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety

class Gardener2(BalancerGreedy): #Example
#class Gardener2(Greedy): # Inherit from the _____ class
    """
    Gardener2 now inherits all the optimized, greedy logic from the Greedy class.
    """
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        # Call the __init__ method of the parent (Greedy) class
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        # FIX: Call the optimized cultivate_garden method from the parent (Greedy) class
        super().cultivate_garden()