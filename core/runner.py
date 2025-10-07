import time
from typing import Type

from core.engine import Engine
from core.garden import Garden
from core.gardener import Gardener
from core.nursery import Nursery


class GameRunner:
    def __init__(
        self,
        simulation_turns: int,
        varieties_file: str | None = None,
        random_count: int | None = None,
        time_limit: float = 60.0,
    ):
        self.varieties_file = varieties_file
        self.random_count = random_count
        self.simulation_turns = simulation_turns
        self.time_limit = time_limit
        self.nursery = Nursery()

    def run(self, gardener_class: Type[Gardener]) -> dict:
        if self.varieties_file:
            varieties = self.nursery.load_from_file(self.varieties_file)
        elif self.random_count:
            varieties = self.nursery.generate_random_varieties(self.random_count)
        else:
            raise ValueError("Must provide either varieties_file or random_count")

        garden = Garden()
        gardener = gardener_class(garden, varieties)

        start_time = time.time()
        gardener.cultivate_garden()
        placement_time = time.time() - start_time

        if placement_time > self.time_limit:
            print(
                f"Warning: Placement exceeded time limit "
                f"({placement_time:.2f}s > {self.time_limit}s)"
            )

        engine = Engine(garden)
        engine.run_simulation(turns=self.simulation_turns)

        return {
            "final_growth": garden.total_growth(),
            "placement_time": placement_time,
            "plants_placed": len(garden.plants),
        }
