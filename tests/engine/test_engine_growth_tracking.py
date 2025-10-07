from core.engine import Engine
from core.micronutrients import Micronutrient
from core.point import Position
from tests.engine.setup_engine import TestEngine


class TestEngineGrowthTracking(TestEngine):
    def test_growth_history_starts_empty(self):
        engine = Engine(self.garden)
        assert len(engine.growth_history) == 0

    def test_growth_history_accumulates(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        plant.micronutrient_inventory = {
            Micronutrient.R: 20.0,
            Micronutrient.G: 20.0,
            Micronutrient.B: 20.0,
        }

        engine = Engine(self.garden)

        engine.run_turn()
        assert len(engine.growth_history) == 1

        engine.run_turn()
        assert len(engine.growth_history) == 2

        engine.run_turn()
        assert len(engine.growth_history) == 3

    def test_total_growth_matches_garden_total(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(10, 5))

        plant1.micronutrient_inventory = {
            Micronutrient.R: 20.0,
            Micronutrient.G: 20.0,
            Micronutrient.B: 20.0,
        }
        plant2.micronutrient_inventory = {
            Micronutrient.R: 20.0,
            Micronutrient.G: 20.0,
            Micronutrient.B: 20.0,
        }

        engine = Engine(self.garden)
        engine.run_simulation(turns=5)

        # Last growth history entry should match garden total
        assert engine.growth_history[-1] == self.garden.total_growth()
