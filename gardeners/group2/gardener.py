import math
import random
from contextlib import suppress

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener2(Gardener):
    """implementing flexible clustering with hex/greedy fallback."""

    # Step size used for greedy fallback grid
    STEP = 0.1

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        # Precompute smallest plant radius to parameterise hex fill grid
        self.min_radius = min((v.radius for v in varieties), default=1.0) if varieties else 1.0

    def cultivate_garden(self) -> None:
        """Main entry point for gardener: build clusters then run fallback."""
        available = list(self.varieties)
        # Stage 1: flexible clustering
        print('Starting flexible cluster placement')
        self._grid_cluster_placement(available)
        # Update internal list to remaining varieties
        self.varieties = available
        # Stage 2: choose fallback based on remaining radii and counts
        if not self.varieties:
            return
        remaining_radii = [v.radius for v in self.varieties]
        if not remaining_radii:
            return
        avg_radius = sum(remaining_radii) / len(remaining_radii)
        # Use hex fill when many small varieties remain, otherwise greedy
        if len(self.varieties) > 1000 or avg_radius < 0.15:
            print('Using hexagonal fill fallback')
            self._hex_fill_fallback()
        else:
            print('Using greedy fallback')
            self._greedy_fallback()

    # cluster placement
    def _grid_cluster_placement(self, available: list[PlantVariety]) -> None:
        """
        Arrange small clusters of three plants on a regular grid.  Clusters
        are placed sequentially on grid points in a hexagonal pattern.
        """
        # Separate varieties by species and sort by production score
        species_lists: dict[Species, list[PlantVariety]] = {
            Species.RHODODENDRON: [],
            Species.GERANIUM: [],
            Species.BEGONIA: [],
        }
        scored: list[tuple[float, PlantVariety]] = []
        for v in available:
            scored.append((self._calculate_net_production_score(v), v))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, v in scored:
            species_lists[v.species].append(v)
        # Determine a base spacing for the grid using the smallest radius
        # Use a cluster spacing multiplier to ensure clusters do not overlap
        cluster_spacing = self.min_radius
        dx = cluster_spacing
        dy = cluster_spacing
        positions: list[tuple[float, float]] = []
        # Generate hex grid positions within garden bounds
        row = 0
        while True:
            cy = row * dy
            if cy == self.garden.height:
                break

            col = 0
            while True:
                cx = col * dx
                if cx == self.garden.width:
                    break
                positions.append((cx, cy))
                col += 1
            row += 1
        # Shuffle positions to avoid bias
        random.shuffle(positions)
        # Place clusters at each grid position
        for cx, cy in positions:
            # Stop if any species is exhausted
            if any(len(species_lists[sp]) == 0 for sp in species_lists):
                break
            # Choose the best variety for each species
            r_variety = species_lists[Species.RHODODENDRON][0]
            g_variety = species_lists[Species.GERANIUM][0]
            b_variety = species_lists[Species.BEGONIA][0]
            cluster_vars = [r_variety, g_variety, b_variety]
            radii = [v.radius for v in cluster_vars]
            lower = max(radii)
            upper = min(radii[i] + radii[j] for i in range(3) for j in range(i + 1, 3))
            if lower >= upper:
                # Cannot form cluster with these varieties; skip this position
                continue
            # Choose compact separation s; lean towards lower bound
            s = lower + (upper - lower) * 0.25
            # For 3 points on a circle, the distance between adjacent plants is d * sqrt(3)
            # So d = s / sqrt(3)
            d = s / math.sqrt(3.0)
            # Define angles for the triangle (0°, 120°, 240°)
            angles = [0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0]
            placements: list[tuple[PlantVariety, Position]] = []
            valid = True
            for variety, angle in zip(cluster_vars, angles, strict=False):
                x = cx + d * math.cos(angle)
                y = cy + d * math.sin(angle)
                pos = Position(x, y)
                if not self.garden.can_place_plant(variety, pos):
                    valid = False
                    break
                placements.append((variety, pos))
            if not valid:
                continue
            # Plant the cluster
            success = True
            for variety, pos in placements:
                if self.garden.add_plant(variety, pos) is None:
                    success = False
                    break
            if not success:
                continue
            # Remove used varieties from lists and available
            for variety, _ in placements:
                with suppress(ValueError):
                    species_lists[variety.species].remove(variety)
                with suppress(ValueError):
                    available.remove(variety)

    # Helper methods for cluster placement
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
        radius_multiplier = 10 - (variety.radius * variety.radius)
        return base_ratio * radius_multiplier

    # Hex fill fallback
    def _hex_fill_fallback(self) -> None:
        """
        Pack remaining varieties onto a hexagonal grid.  At each grid cell
        choose the variety that produces the most deficient nutrient, falling
        back to secondary species if no variety of the target species fits.
        """
        # Build species lists keyed by score
        species_lists: dict[Species, list[tuple[float, PlantVariety]]] = {
            Species.RHODODENDRON: [],
            Species.GERANIUM: [],
            Species.BEGONIA: [],
        }
        for v in self.varieties:
            score = self._calculate_net_production_score(v)
            species_lists[v.species].append((score, v))
        for sp in species_lists:
            species_lists[sp].sort(key=lambda x: x[0], reverse=True)
        # Generate hex grid positions
        positions = self._generate_hex_grid_positions()
        for pos in positions:
            # Determine which species is most deficient
            underrepresented = self._get_species_for_most_deficient_nutrient()
            if not underrepresented:
                break
            target_value = next(iter(underrepresented))
            target_species = Species(target_value)
            chosen_variety = None
            # Try to pick a variety of the target species that fits at this position
            for score, variety in list(species_lists[target_species]):  # noqa: B007
                if self.garden.can_place_plant(variety, pos):
                    chosen_variety = variety
                    break
            # If none fits, try alternate species
            if chosen_variety is None:
                for alt_species in [Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA]:
                    for score, variety in list(species_lists[alt_species]):  # noqa: B007
                        if self.garden.can_place_plant(variety, pos):
                            chosen_variety = variety
                            target_species = alt_species
                            break
                    if chosen_variety:
                        break
            if chosen_variety is None:
                continue
            # Plant and remove the variety from lists
            if self.garden.add_plant(chosen_variety, pos) is not None:
                with suppress(ValueError):
                    species_lists[target_species].remove(
                        next(
                            (
                                item
                                for item in species_lists[target_species]
                                if item[1] is chosen_variety
                            ),
                            None,
                        )
                    )
                with suppress(ValueError):
                    self.varieties.remove(chosen_variety)

    # Greedy fallback

    def _greedy_fallback(self) -> None:
        """
        Place remaining plants one by one using a greedy strategy that
        addresses the most deficient nutrient first and maximises potential
        interactions at each step.
        """
        plantable_varieties = self._get_sorted_varieties()
        candidate_positions = self._generate_placement_grid()
        is_first_plant = not self.garden.plants
        while plantable_varieties:
            underrepresented_species = self._get_underrepresented_species()
            if not underrepresented_species:
                break
            best_variety_tuple = self._find_best_variety_to_plant(
                plantable_varieties, underrepresented_species
            )
            if best_variety_tuple is None:
                break
            _, best_variety = best_variety_tuple
            best_position: Position | None = None
            max_interactions = -1
            # For the first plant, try placing at the centre
            if is_first_plant:
                centre = Position(self.garden.width / 2.0, self.garden.height / 2.0)
                if self.garden.can_place_plant(best_variety, centre):
                    best_position = centre
                is_first_plant = False
            if best_position is None:
                for pos in candidate_positions:
                    if not self.garden.can_place_plant(best_variety, pos):
                        continue
                    interactions = self._count_potential_interactions_strict_balanced(
                        best_variety, pos
                    )
                    if interactions > max_interactions:
                        max_interactions = interactions
                        best_position = pos
            if best_position is None:
                break
            plant = self.garden.add_plant(best_variety, best_position)
            if plant is not None:
                # Remove the planted variety from list
                for i, (_score, variety) in enumerate(plantable_varieties):
                    if id(variety) == id(best_variety):
                        plantable_varieties.pop(i)
                        break
                # Remove the used position to prevent reuse
                with suppress(ValueError):
                    candidate_positions.remove(best_position)
            else:
                break

    # Helpers for greedy
    def _generate_hex_grid_positions(self) -> list[Position]:
        """Generate positions on a hexagonal (triangular) grid."""
        positions: list[Position] = []
        R = self.min_radius
        dx = R
        dy = R
        row = 0
        while True:
            y = row * dy
            if y > self.garden.height:
                break

            col = 0
            while True:
                x = col * dx
                if x > self.garden.width:
                    break
                positions.append(Position(x, y))
                col += 1
            row += 1
        return positions

    def _calculate_net_production_score(self, variety: PlantVariety) -> float:
        """Compute a score based on production vs. consumption and radius."""
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
        # Prefer smaller radii: penalise radius squared
        radius_multiplier = 10 - (variety.radius * variety.radius)
        return base_ratio * radius_multiplier

    def _get_sorted_varieties(self) -> list[tuple[float, PlantVariety]]:
        """Return all remaining varieties sorted by net production score."""
        scored: list[tuple[float, PlantVariety]] = []
        for v in self.varieties:
            score = self._calculate_net_production_score(v)
            scored.append((score, v))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _get_current_net_nutrients(self) -> dict[Micronutrient, float]:
        """Compute current net nutrient balances for existing plants."""
        net = {m: 0.0 for m in Micronutrient}
        for plant in self.garden.plants:
            coeffs = plant.variety.nutrient_coefficients
            for nutrient, amount in coeffs.items():
                net[nutrient] += amount
        return net

    def _get_species_for_most_deficient_nutrient(self) -> set[str]:
        """Return the species producing the nutrient with the lowest net value."""
        net = self._get_current_net_nutrients()
        if not net:
            return {Species.RHODODENDRON.value}
        min_val = min(net.values())
        def_nutrients = [nut for nut, val in net.items() if val == min_val]
        if Micronutrient.R in def_nutrients:
            return {Species.RHODODENDRON.value}
        if Micronutrient.G in def_nutrients:
            return {Species.GERANIUM.value}
        return {Species.BEGONIA.value}

    # Alias for greedy fallbacks
    _get_underrepresented_species = _get_species_for_most_deficient_nutrient

    def _find_best_variety_to_plant(
        self, scored_varieties: list[tuple[float, PlantVariety]], underrepresented_species: set[str]
    ) -> tuple[float, PlantVariety] | None:
        """Find the highest scoring variety belonging to the underrepresented species."""
        if not scored_varieties or not underrepresented_species:
            return None
        target_value = next(iter(underrepresented_species))
        for score, variety in scored_varieties:
            if variety.species.value == target_value:
                return (score, variety)
        return None

    def _generate_placement_grid(self) -> list[Position]:
        """Generate a uniform grid of candidate positions for greedy placement."""
        positions: list[Position] = []
        step = self.STEP
        y = step
        while y < self.garden.height - step:
            x = step
            while x < self.garden.width - step:
                positions.append(Position(x, y))
                x += step
            y += step
        return positions

    def _count_potential_interactions_strict_balanced(
        self, variety: PlantVariety, position: Position
    ) -> int:
        """
        Count the number of complementary species this plant could interact with if planted.

        The strict‑balanced rule awards interactions only if the plant interacts with all
        complementary species.  Otherwise, a single interaction is counted if any
        complementary interaction exists.  No interactions are counted if none exist.
        """
        total = 0
        interacting_species = set()
        new_radius = variety.radius
        for existing in self.garden.plants:
            # Ignore same species for interaction potential
            if existing.variety.species == variety.species:
                continue
            distance = self.garden._calculate_distance(position, existing.position)
            interaction_distance = new_radius + existing.variety.radius
            if distance < interaction_distance:
                total += 1
                interacting_species.add(existing.variety.species)
        all_species = {Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA}
        complementary = all_species - {variety.species}
        if interacting_species.issuperset(complementary):
            return total
        elif interacting_species:
            return 1
        return 0
