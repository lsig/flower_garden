from core.exchange import NutrientExchange
from core.garden import Garden


class Engine:
    def __init__(self, garden: Garden) -> None:
        self.garden = garden
        self.nutrient_exchange = NutrientExchange(garden=garden)
        self.turn = 0
        self.growth_history: list[float] = []

    def _daytime_production(self) -> None:
        for plant in self.garden.plants:
            plant.produce()

    def _evening_exchange(self) -> None:
        self.nutrient_exchange.execute()

    def _overnight_growth(self) -> float:
        turn_growth = 0.0

        for plant in self.garden.plants:
            turn_growth += plant.grow()

        return turn_growth

    def run_turn(self):
        self._daytime_production()
        self._evening_exchange()
        growth = self._overnight_growth()

        total_growth = self.garden.total_growth()
        self.growth_history.append(total_growth)
        self.turn += 1

        return growth

    def run_simulation(self, turns: int) -> list[float]:
        for _ in range(turns):
            self.run_turn()

        return self.growth_history
