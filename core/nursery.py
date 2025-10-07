import json
import random

from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species


class Nursery:
    def __init__(self):
        self.varieties: list[PlantVariety] = []

    def load_from_file(self, filepath: str) -> list[PlantVariety]:
        with open(filepath, "r") as f:
            data = json.load(f)

        seed = data.get("seed")
        if seed is not None:
            random.seed(seed)

        varieties = []
        for item in data["varieties"]:
            count = item.get("count", 1)

            # NOTE: Create separate instances for each count
            for _ in range(count):
                variety = PlantVariety(
                    name=item["name"],
                    radius=item["radius"],
                    species=Species[item["species"]],
                    nutrient_coefficients={
                        Micronutrient[k]: v
                        for k, v in item["nutrient_coefficients"].items()
                    },
                )
                self._validate_variety(variety)
                varieties.append(variety)

        self.varieties = varieties
        return varieties

    def _validate_variety(self, variety: PlantVariety) -> None:
        if variety.radius not in [1, 2, 3]:
            raise ValueError(
                f"Invalid radius {variety.radius} for {variety.name}. "
                f"Radius must be 1, 2, or 3."
            )

        coeffs = variety.nutrient_coefficients
        r = coeffs[Micronutrient.R]
        g = coeffs[Micronutrient.G]
        b = coeffs[Micronutrient.B]

        min_val = -2 * variety.radius
        max_val = 2 * variety.radius

        for nutrient, coeff in coeffs.items():
            if not (min_val <= coeff <= max_val):
                raise ValueError(
                    f"Invalid coefficient for {nutrient} in {variety.name}: {coeff}. "
                    f"Must be between {min_val} and {max_val}."
                )

        if variety.species == Species.RHODODENDRON:
            if not (r > 0 and g < 0 and b < 0):
                raise ValueError(
                    f"Invalid coefficients for Rhododendron {variety.name}. "
                    f"Must have R > 0, G < 0, B < 0. Got R={r}, G={g}, B={b}."
                )
        elif variety.species == Species.GERANIUM:
            if not (g > 0 and r < 0 and b < 0):
                raise ValueError(
                    f"Invalid coefficients for Geranium {variety.name}. "
                    f"Must have G > 0, R < 0, B < 0. Got R={r}, G={g}, B={b}."
                )
        elif variety.species == Species.BEGONIA:
            if not (b > 0 and r < 0 and g < 0):
                raise ValueError(
                    f"Invalid coefficients for Begonia {variety.name}. "
                    f"Must have B > 0, R < 0, G < 0. Got R={r}, G={g}, B={b}."
                )

        if r + g + b <= 0:
            raise ValueError(
                f"Invalid coefficients for {variety.name}: sum is {r + g + b}. "
                f"Net micronutrient production (R+G+B) must be positive."
            )

    def generate_random_varieties(self, count: int) -> list[PlantVariety]:
        varieties = []
        species_list = [Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA]

        for i in range(count):
            species = random.choice(species_list)
            radius = random.choice([1, 2, 3])

            coefficients = self._generate_valid_coefficients(species, radius)

            variety = PlantVariety(
                name=f"{species.value}_{i + 1}",
                radius=radius,
                species=species,
                nutrient_coefficients=coefficients,
            )

            self._validate_variety(variety)
            varieties.append(variety)

        self.varieties = varieties
        return varieties

    def _generate_valid_coefficients(
        self, species: Species, radius: int
    ) -> dict[Micronutrient, float]:
        min_val = -2 * radius
        max_val = 2 * radius

        if species == Species.RHODODENDRON:
            produced, consumed1, consumed2 = (
                Micronutrient.R,
                Micronutrient.G,
                Micronutrient.B,
            )
        elif species == Species.GERANIUM:
            produced, consumed1, consumed2 = (
                Micronutrient.G,
                Micronutrient.R,
                Micronutrient.B,
            )
        else:  # BEGONIA
            produced, consumed1, consumed2 = (
                Micronutrient.B,
                Micronutrient.R,
                Micronutrient.G,
            )

        produced_val = random.uniform(0.2, max_val)

        max_consumed_total = produced_val - 0.1

        consumed1_abs = random.uniform(0.1, min(max_consumed_total * 0.6, -min_val))
        consumed2_abs = random.uniform(
            0.1, min(max_consumed_total - consumed1_abs, -min_val)
        )

        consumed1_val = -consumed1_abs
        consumed2_val = -consumed2_abs

        return {
            produced: round(produced_val, 2),
            consumed1: round(consumed1_val, 2),
            consumed2: round(consumed2_val, 2),
        }

    def get_varieties(self) -> list[PlantVariety]:
        return self.varieties
