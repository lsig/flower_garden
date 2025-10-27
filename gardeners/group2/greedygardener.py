
from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class GreedyVersion1(Gardener):
    STEP = 0.2

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.min_available_radius = (
            min([v.radius for v in varieties], default=1.0) if varieties else 1.0
        )

    def _calculate_net_production_score(self, variety: PlantVariety) -> float:
        coeffs = variety.nutrient_coefficients

        production = 0.0
        total_consumption = 0.0

        if variety.species == Species.RHODODENDRON:
            production = coeffs.get(Micronutrient.R, 0.0)
            total_consumption = abs(coeffs.get(Micronutrient.G, 0.0)) + abs(
                coeffs.get(Micronutrient.B, 0.0)
            )
        elif variety.species == Species.GERANIUM:
            production = coeffs.get(Micronutrient.G, 0.0)
            total_consumption = abs(coeffs.get(Micronutrient.R, 0.0)) + abs(
                coeffs.get(Micronutrient.B, 0.0)
            )
        elif variety.species == Species.BEGONIA:
            production = coeffs.get(Micronutrient.B, 0.0)
            total_consumption = abs(coeffs.get(Micronutrient.R, 0.0)) + abs(
                coeffs.get(Micronutrient.G, 0.0)
            )
        else:
            return 0.0

        if total_consumption <= 0:
            return float('inf')

        base_ratio = production / total_consumption

        radius_multiplier = 4 - variety.radius

        composite_score = base_ratio * radius_multiplier

        return composite_score

    def _get_sorted_varieties(self) -> list[tuple[float, PlantVariety]]:
        scored_varieties = []
        for variety in self.varieties:
            score = self._calculate_net_production_score(variety)
            scored_varieties.append((score, variety))
        scored_varieties.sort(key=lambda x: x[0], reverse=True)
        return scored_varieties

    def _get_species_counts(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Species}
        for plant in self.garden.plants:
            counts[plant.variety.species.value] += 1
        return counts

    def _get_underrepresented_species(self) -> set[str]:
        species_counts = self._get_species_counts()
        min_count = min(species_counts.values())
        return {s for s, count in species_counts.items() if count == min_count}

    def _find_best_variety_to_plant(
        self, scored_varieties: list[tuple[float, PlantVariety]], underrepresented_species: set[str]
    ) -> tuple[float, PlantVariety] | None:
        if not scored_varieties:
            return None

        for score, variety in scored_varieties:
            if variety.species.value in underrepresented_species:
                return (score, variety)

        return scored_varieties[0]

    def _generate_placement_grid(self) -> list[Position]:
        positions = []
        step = self.STEP

        start_x = step
        start_y = step

        y = start_y
        while y < self.garden.height - step:
            x = start_x
            while x < self.garden.width - step:
                positions.append(Position(x, y))
                x += step
            y += step

        return positions

    def _count_potential_interactions(self, variety: PlantVariety, position: Position) -> int:
        count = 0
        new_radius = variety.radius

        for existing_plant in self.garden.plants:
            if existing_plant.variety.species == variety.species:
                continue

            distance = self.garden._calculate_distance(position, existing_plant.position)
            interaction_distance = new_radius + existing_plant.variety.radius

            if distance < interaction_distance:
                count += 1

        return count

    def cultivate_garden(self) -> None:
        plantable_varieties = self._get_sorted_varieties()
        candidate_positions = self._generate_placement_grid()

        while plantable_varieties:
            underrepresented_species = self._get_underrepresented_species()

            best_variety_tuple = self._find_best_variety_to_plant(
                plantable_varieties, underrepresented_species
            )

            if not best_variety_tuple:
                break

            best_score, best_variety = best_variety_tuple

            best_placement: tuple[Position, int] | None = None
            max_interactions = -1

            for position in candidate_positions:
                if not self.garden.can_place_plant(best_variety, position):
                    continue

                interactions = self._count_potential_interactions(best_variety, position)

                if interactions > max_interactions:
                    max_interactions = interactions
                    best_placement = (position, interactions)

            if best_placement:
                best_position, _ = best_placement

                plant = self.garden.add_plant(best_variety, best_position)

                if plant is not None:
                    for i, (_score, variety) in enumerate(plantable_varieties):
                        if id(variety) == id(best_variety):
                            plantable_varieties.pop(i)
                            break

                    if best_position in candidate_positions:
                        candidate_positions.remove(best_position)
            else:
                break
