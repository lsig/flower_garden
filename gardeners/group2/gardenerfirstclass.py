# Assuming this import works based on your file structure
from contextlib import suppress

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener2(Gardener):
    STEP = 0.1  # Smaller = better but slower

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.min_available_radius = (
            min([v.radius for v in varieties], default=1.0) if varieties else 1.0
        )

    # Variety Selection Strategy: Composite Score (Efficiency + Radius)

    def _calculate_net_production_score(self, variety: PlantVariety) -> float:
        coeffs = variety.nutrient_coefficients

        production = 0.0
        total_consumption = 0.0

        if variety.species == Species.RHODODENDRON:
            production = coeffs.get(Micronutrient.R, 0.0)
            # RHODODENDRON produces R, consumes G and B
            total_consumption = abs(coeffs.get(Micronutrient.G, 0.0)) + abs(
                coeffs.get(Micronutrient.B, 0.0)
            )
        elif variety.species == Species.GERANIUM:
            production = coeffs.get(Micronutrient.G, 0.0)
            # GERANIUM produces G, consumes R and B
            total_consumption = abs(coeffs.get(Micronutrient.R, 0.0)) + abs(
                coeffs.get(Micronutrient.B, 0.0)
            )
        elif variety.species == Species.BEGONIA:
            production = coeffs.get(Micronutrient.B, 0.0)
            # BEGONIA produces B, consumes R and G
            total_consumption = abs(coeffs.get(Micronutrient.R, 0.0)) + abs(
                coeffs.get(Micronutrient.G, 0.0)
            )
        else:
            return 0.0

        if total_consumption <= 0:
            return float('inf')

        base_ratio = production / total_consumption

        radius_multiplier = 10 - (variety.radius * variety.radius)

        composite_score = base_ratio * radius_multiplier

        return composite_score

    def _get_sorted_varieties(self) -> list[tuple[float, PlantVariety]]:
        """Sorts all available varieties by their composite score (descending)."""
        scored_varieties = []
        for variety in self.varieties:
            score = self._calculate_net_production_score(variety)
            scored_varieties.append((score, variety))
        scored_varieties.sort(key=lambda x: x[0], reverse=True)
        return scored_varieties

    # Species Balancing Logic

    def _get_current_net_nutrients(self) -> dict[Micronutrient, float]:
        """Calculates the current net amount of each micronutrient in the system."""
        net_nutrients = {m: 0.0 for m in Micronutrient}

        for plant in self.garden.plants:
            coeffs = plant.variety.nutrient_coefficients
            for nutrient, amount in coeffs.items():
                net_nutrients[nutrient] += amount

        return net_nutrients

    def _get_species_for_most_deficient_nutrient(self) -> set[str]:
        """
        Identifies the species that produces the most deficient micronutrient.
        """
        net_nutrients = self._get_current_net_nutrients()

        # Determine the most deficient nutrient (lowest net value)
        if not net_nutrients:
            # Turn 1, place R down first
            most_deficient_nutrient = Micronutrient.R
        else:
            # Find the minimum net nutrient
            min_net_value = min(net_nutrients.values())
            deficient_nutrients = [
                nutrient for nutrient, value in net_nutrients.items() if value == min_net_value
            ]

            # Tiebreaker: R, G, B
            if Micronutrient.R in deficient_nutrients:
                most_deficient_nutrient = Micronutrient.R
            elif Micronutrient.G in deficient_nutrients:
                most_deficient_nutrient = Micronutrient.G
            elif Micronutrient.B in deficient_nutrients:
                most_deficient_nutrient = Micronutrient.B
            else:
                # Shouldn't reach here
                return set()
        if most_deficient_nutrient == Micronutrient.R:
            return {Species.RHODODENDRON.value}
        elif most_deficient_nutrient == Micronutrient.G:
            return {Species.GERANIUM.value}
        elif most_deficient_nutrient == Micronutrient.B:
            return {Species.BEGONIA.value}

        return set()  # Just in case

    _get_underrepresented_species = _get_species_for_most_deficient_nutrient

    def _find_best_variety_to_plant(
        self, scored_varieties: list[tuple[float, PlantVariety]], underrepresented_species: set[str]
    ) -> tuple[float, PlantVariety] | None:
        """
        Selects the single highest-scoring variety that belongs to the "fixing" species.
        """
        if not scored_varieties or not underrepresented_species:
            return None

        target_species_value = next(iter(underrepresented_species))

        for score, variety in scored_varieties:
            if variety.species.value == target_species_value:
                return (score, variety)

        # If we can't place anymore down, then we stop the simulation
        return None

    # --- Placement Strategy ---

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
        """Counts # interaction"""
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

    # --- Main Cultivation Method ---

    def cultivate_garden(self) -> None:
        plantable_varieties = self._get_sorted_varieties()
        candidate_positions = self._generate_placement_grid()

        # Check if this is the very first plant placement
        is_first_plant = not self.garden.plants  # 👈 MODIFICATION START

        while plantable_varieties:
            # 1. Determine the species needed to fix the nutrient deficiency
            underrepresented_species = self._get_underrepresented_species()
            if not underrepresented_species:
                break

            # 2. Find the single best variety to plant based on score and balance
            best_variety_tuple = self._find_best_variety_to_plant(
                plantable_varieties, underrepresented_species
            )

            if best_variety_tuple is None:
                break

            best_score, best_variety = best_variety_tuple
            best_position = None

            # --- First Plant Logic: Place in the Middle ---
            if is_first_plant:
                center_x = self.garden.width / 2
                center_y = self.garden.height / 2
                potential_center_position = Position(center_x, center_y)

                if self.garden.can_place_plant(best_variety, potential_center_position):
                    best_position = potential_center_position
                    is_first_plant = False  # Ensure subsequent plants use normal logic
                else:
                    # Fallback to normal placement if the center isn't valid for the plant
                    is_first_plant = False

            # 3. Find a good position (Normal logic, only runs if not first plant)
            if best_position is None:
                best_placement: tuple[Position, int] | None = None
                max_interactions = -1

                for position in candidate_positions:
                    if not self.garden.can_place_plant(best_variety, position):
                        continue

                    interactions = self._count_potential_interactions(best_variety, position)

                    # Selection Criteria: Maximize interactions
                    if interactions > max_interactions:
                        max_interactions = interactions
                        best_placement = (position, interactions)

                if best_placement:
                    best_position, _ = best_placement
                else:
                    # Could not find a single place to put the highest-priority plant.
                    break
            # 👈 MODIFICATION END

            # 4. Execute the placement
            if best_position:
                plant = self.garden.add_plant(best_variety, best_position)

                if plant is not None:
                    # Placement succeeded
                    for i, (_score, variety) in enumerate(plantable_varieties):
                        if id(variety) == id(best_variety):
                            plantable_varieties.pop(i)
                            break
                    with suppress(ValueError):
                        # Remove the position from the candidate grid if it was in there
                        candidate_positions.remove(best_position)
                else:
                    # Placement failed (e.g., radius issue)
                    break
            else:
                # No valid position found
                break
