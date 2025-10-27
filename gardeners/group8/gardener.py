from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position
from core.micronutrients import Micronutrient
import math


class Gardener8(Gardener):
    """Cultivates the garden using optimized, non-overlapping RGB clusters."""

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        triage = self.generate_triage()
        print("Top 5 triage scores and combinations:")
        for score, r, g, b in triage[:5]:
            print(f"Score: {score:.2f}, R: {r.name} , G: {g.name}, B: {b.name}")
        #TODO: Need a placing function

    def generate_triage(self):
        """Generate all possible RGB triage and score them."""
        species_map = {
            Species.RHODODENDRON: [],
            Species.GERANIUM: [],
            Species.BEGONIA: []
        }

        for variety in self.varieties:
            if variety.species in species_map:
                species_map[variety.species].append(variety)

        triage = [
            (self.score_triage(r, g, b), r, g, b)
            for r in species_map[Species.RHODODENDRON]
            for g in species_map[Species.GERANIUM]
            for b in species_map[Species.BEGONIA]
        ]

        return sorted(triage, key=lambda x: x[0], reverse=True)

    def score_triage(self, r, g, b):
        """Score a cluster by growth rate x nutrient sustainability."""
        # production of nutrients
        prod = {
            Micronutrient.R: r.nutrient_coefficients[Micronutrient.R],
            Micronutrient.G: g.nutrient_coefficients[Micronutrient.G],
            Micronutrient.B: b.nutrient_coefficients[Micronutrient.B],
        }
        # nutrient consumption as the sum of absolute values of negative coefficients
        cons = {
            Micronutrient.R: abs(g.nutrient_coefficients[Micronutrient.R]) + abs(b.nutrient_coefficients[Micronutrient.R]),
            Micronutrient.G: abs(r.nutrient_coefficients[Micronutrient.G]) + abs(b.nutrient_coefficients[Micronutrient.G]),
            Micronutrient.B: abs(r.nutrient_coefficients[Micronutrient.B]) + abs(g.nutrient_coefficients[Micronutrient.B]),
        }

        # nutrient score is the minimum surplus across all nutrients
        nutrient_score = min(prod[n] - cons[n] for n in prod)

        # growth rate is the sum of the radii
        growth_rate = r.radius + g.radius + b.radius

        return nutrient_score * 0.8 + growth_rate * 0.2