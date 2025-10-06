from core.point import Position
from tests.garden.garden_setup import TestGarden


class TestGardenInteractions(TestGarden):
    def test_get_interacting_plants_no_interactions(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(0, 0))
        plant2 = self.garden.add_plant(self.rhodo_variety, Position(10, 10))

        interactions1 = self.garden.get_interacting_plants(plant1)
        interactions2 = self.garden.get_interacting_plants(plant2)

        assert len(interactions1) == 0
        assert len(interactions2) == 0

    def test_same_species_do_not_interact(self):
        # Place two Geraniums close enough that roots would overlap
        plant1 = self.garden.add_plant(self.geranium_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        # But same species should NOT interact
        interactions1 = self.garden.get_interacting_plants(plant1)
        interactions2 = self.garden.get_interacting_plants(plant2)

        assert len(interactions1) == 0
        assert len(interactions2) == 0

    def test_get_interacting_plants_one_interaction(self):
        # Rhodo (r=2) at (5,5) and Geranium (r=1)
        # Geranium needs distance >= 1 to place
        # For interaction: distance < 3 (2+1)
        # Place geranium at distance 1.5: legal and interacting
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        interactions1 = self.garden.get_interacting_plants(plant1)
        interactions2 = self.garden.get_interacting_plants(plant2)

        assert len(interactions1) == 1
        assert plant2 in interactions1
        assert len(interactions2) == 1
        assert plant1 in interactions2

    def test_get_interacting_plants_multiple_interactions(self):
        # Place all three species close enough to interact
        # Rhodo (r=2), Geranium (r=1), Begonia (r=3)
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(
            self.geranium_variety, Position(6.5, 5)
        )  # dist 1.5 < 3
        plant3 = self.garden.add_plant(
            self.begonia_variety, Position(6, 8)
        )  # dist ~3.2 < 5

        interactions1 = self.garden.get_interacting_plants(plant1)

        # Rhodo should interact with both Geranium and Begonia
        assert len(interactions1) == 2
        assert plant2 in interactions1
        assert plant3 in interactions1

    def test_get_interacting_plants_at_exact_boundary(self):
        # Rhodo (r=2) and Geranium (r=1): interaction boundary at distance = 3
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(
            self.geranium_variety, Position(8, 5)
        )  # Distance = 3

        interactions1 = self.garden.get_interacting_plants(plant1)
        interactions2 = self.garden.get_interacting_plants(plant2)

        assert len(interactions1) == 0
        assert len(interactions2) == 0

    def test_get_all_interactions_empty_garden(self):
        interactions = self.garden.get_all_interactions()
        assert len(interactions) == 0

    def test_get_all_interactions_no_overlaps(self):
        self.garden.add_plant(self.rhodo_variety, Position(2, 2))
        self.garden.add_plant(self.geranium_variety, Position(10, 2))
        self.garden.add_plant(self.begonia_variety, Position(2, 8))

        interactions = self.garden.get_all_interactions()
        assert len(interactions) == 0

    def test_get_all_interactions_one_pair(self):
        plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        plant2 = self.garden.add_plant(self.geranium_variety, Position(6.5, 5))

        interactions = self.garden.get_all_interactions()

        assert len(interactions) == 1
        assert (plant1, plant2) in interactions or (plant2, plant1) in interactions

    def test_get_all_interactions_no_duplicates(self):
        # Triangle of three different species, all interacting
        _plant1 = self.garden.add_plant(self.rhodo_variety, Position(5, 5))
        _plant2 = self.garden.add_plant(
            self.geranium_variety, Position(6.5, 5)
        )  # dist 1.5 < 3
        _plant3 = self.garden.add_plant(
            self.begonia_variety, Position(6, 8)
        )  # close to both

        interactions = self.garden.get_all_interactions()

        # Should have 3 unique pairs
        assert len(interactions) == 3

        interaction_ids = [frozenset([id(p1), id(p2)]) for p1, p2 in interactions]
        assert len(interaction_ids) == len(set(interaction_ids))
