from core.micronutrients import Micronutrient
from core.nursery import Nursery
from core.plants.species import Species


class TestNurseryRandomGeneration:
    def test_generate_random_varieties(self):
        nursery = Nursery()
        varieties = nursery.generate_random_varieties(count=10)

        assert len(varieties) == 10

        # All should be valid
        for variety in varieties:
            assert variety.radius in [1, 2, 3]
            assert variety.species in [
                Species.RHODODENDRON,
                Species.GERANIUM,
                Species.BEGONIA,
            ]

    def test_random_varieties_meet_constraints(self):
        nursery = Nursery()
        varieties = nursery.generate_random_varieties(count=20)

        for variety in varieties:
            coeffs = variety.nutrient_coefficients
            r = coeffs[Micronutrient.R]
            g = coeffs[Micronutrient.G]
            b = coeffs[Micronutrient.B]

            # Check range
            assert -2 * variety.radius <= r <= 2 * variety.radius
            assert -2 * variety.radius <= g <= 2 * variety.radius
            assert -2 * variety.radius <= b <= 2 * variety.radius

            # Check net positive
            assert r + g + b > 0

            # Check species constraints
            if variety.species == Species.RHODODENDRON:
                assert r > 0 and g < 0 and b < 0
            elif variety.species == Species.GERANIUM:
                assert g > 0 and r < 0 and b < 0
            elif variety.species == Species.BEGONIA:
                assert b > 0 and r < 0 and g < 0

    def test_get_varieties_returns_generated_list(self):
        nursery = Nursery()
        generated = nursery.generate_random_varieties(count=5)

        retrieved = nursery.get_varieties()

        assert len(retrieved) == 5
        assert retrieved == generated
