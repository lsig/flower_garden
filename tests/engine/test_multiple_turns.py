from core.engine import Engine
from core.micronutrients import Micronutrient
from core.point import Position
from tests.engine.setup_engine import TestEngine


class TestEngineMultipleTurns(TestEngine):
    def test_run_simulation_executes_multiple_turns(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        engine = Engine(self.garden)
        history = engine.run_simulation(turns=5)

        assert engine.turn == 5
        assert len(history) == 5
        assert len(engine.growth_history) == 5

    def test_growth_history_tracks_cumulative_growth(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        # Give abundant nutrients
        plant.micronutrient_inventory = {
            Micronutrient.R: 20.0,
            Micronutrient.G: 20.0,
            Micronutrient.B: 20.0,
        }

        engine = Engine(self.garden)
        engine.run_simulation(turns=3)

        # Growth should be cumulative and non-decreasing
        for i in range(len(engine.growth_history) - 1):
            assert engine.growth_history[i + 1] >= engine.growth_history[i]

    def test_interacting_plants_grow_through_exchange(self):
        # Two interacting plants of different species
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        engine = Engine(self.garden)

        # Run multiple turns
        engine.run_simulation(turns=10)

        # Both plants should have grown through production and exchange
        assert plant1.size > 0
        assert plant2.size > 0

    def test_growth_stops_at_max_size(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        # Set plant near max size
        plant.size = plant.max_size - plant.variety.radius

        # Give abundant nutrients
        plant.micronutrient_inventory = {
            Micronutrient.R: 20.0,
            Micronutrient.G: 20.0,
            Micronutrient.B: 20.0,
        }

        engine = Engine(self.garden)
        engine.run_simulation(turns=5)

        # Should stop at max size
        assert plant.size == plant.max_size

    def test_empty_garden_runs_without_error(self):
        engine = Engine(self.garden)  # Empty garden

        history = engine.run_simulation(turns=10)

        # Should complete without error
        assert len(history) == 10
        assert all(growth == 0.0 for growth in history)
