from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
import random
from core.point import Position

class Gardener1(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def knapSack(self, capacity, val, wt):

        # 1D matrix for tabulation.
        dp = [0] * (capacity + 1)

        # Calculate maximum profit for each
        # item index and knapsack weight.
        for i in range(len(val) - 1, -1, -1):
            for j in range(1, capacity + 1):

                take = 0
                if j - wt[i] >= 0:
                    take = val[i] + dp[j - wt[i]]
                noTake = dp[j]

                dp[j] = max(take, noTake)

        return dp[capacity]
    

    # smallest width you can have is 3.
    # largest width is 9.

    # placing things on the corner is suitable because it is easier to get rid of a lot of area.

    def cultivate_garden(self) -> None:
        for variety in self.varieties:
            print(variety.radius)
            for coeff in variety.nutrient_coefficients.items():
                print(coeff)
            print()
            x = random.uniform(0, self.garden.width)
            y = random.uniform(0, self.garden.height)

            position = Position(x, y)

            self.garden.add_plant(variety, position)

