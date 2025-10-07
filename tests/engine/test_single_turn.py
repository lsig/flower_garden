from core.engine import Engine
from core.micronutrients import Micronutrient
from core.point import Position
from tests.engine.setup_engine import TestEngine


class TestEngineSingleTurn(TestEngine):
    def test_run_turn_executes_all_phases(self):
        # Place two interacting plants
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        engine = Engine(self.garden)

        # Initially no growth
        assert engine.turn == 0
        assert len(engine.growth_history) == 0

        # Run one turn
        turn_growth = engine.run_turn()

        # Turn incremented
        assert engine.turn == 1

        # Growth history updated
        assert len(engine.growth_history) == 1

        # Growth should be non-negative
        assert turn_growth >= 0.0

    def test_daytime_production_increases_nutrients(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        initial_r = plant.micronutrient_inventory[Micronutrient.R]

        engine = Engine(self.garden)
        engine._daytime_production()

        # R should increase (rhodo produces R)
        assert plant.micronutrient_inventory[Micronutrient.R] > initial_r

    def test_evening_exchange_transfers_nutrients(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        # Set up inventories for exchange
        plant1.micronutrient_inventory[Micronutrient.R] = 12.0
        plant2.micronutrient_inventory[Micronutrient.G] = 12.0

        initial_plant1_g = plant1.micronutrient_inventory[Micronutrient.G]
        initial_plant2_r = plant2.micronutrient_inventory[Micronutrient.R]

        engine = Engine(self.garden)
        engine._evening_exchange()

        # Both plants should have received nutrients
        assert plant1.micronutrient_inventory[Micronutrient.G] > initial_plant1_g
        assert plant2.micronutrient_inventory[Micronutrient.R] > initial_plant2_r

    def test_overnight_growth_with_sufficient_nutrients(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        # Give plant enough nutrients to grow
        plant.micronutrient_inventory = {
            Micronutrient.R: 10.0,
            Micronutrient.G: 10.0,
            Micronutrient.B: 10.0,
        }

        engine = Engine(self.garden)
        growth = engine._overnight_growth()

        # Should have grown
        assert growth == plant.variety.radius  # Grew by radius amount
        assert plant.size == plant.variety.radius

    def test_overnight_growth_with_insufficient_nutrients(self):
        plant = self.garden.add_plant(self.rhodo_variety, Position(5, 5))

        # Not enough nutrients (need 4 of each for radius 2)
        plant.micronutrient_inventory = {
            Micronutrient.R: 3.0,
            Micronutrient.G: 3.0,
            Micronutrient.B: 3.0,
        }

        engine = Engine(self.garden)
        growth = engine._overnight_growth()

        # Should not have grown
        assert growth == 0.0
        assert plant.size == 0.0
