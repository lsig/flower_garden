from core.engine import Engine
from core.point import Position
from tests.engine.setup_engine import TestEngine


class TestEngineComplexScenarios(TestEngine):
    def test_three_species_ecosystem(self):
        # Create a small ecosystem with all three species
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))
        plant3 = self.garden.add_plant(self.begonia_variety, Position(5, 9))

        engine = Engine(self.garden)
        engine.run_simulation(turns=20)

        # All plants should have grown
        assert plant1.size > 0
        assert plant2.size > 0
        assert plant3.size > 0

        # Total growth should be positive
        assert engine.growth_history[-1] > 0

    def test_isolated_plant_has_limited_growth(self):
        # Single plant with no exchange partners
        # Rhododendron produces R but needs G and B
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        engine = Engine(self.garden)
        engine.run_simulation(turns=10)

        # Should grow a little from initial nutrients, then stop
        assert plant.size > 0  # Grew some
        assert plant.size < plant.max_size  # But not to full size

        # Should be stuck (no more G or B without exchange)
        final_size = plant.size
        engine.run_simulation(turns=10)  # Run more turns
        assert plant.size == final_size  # No additional growth
        assert plant.size == 4
