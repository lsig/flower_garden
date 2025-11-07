import math

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener1f(Gardener):
    """
    Two-phase strategy:
    1. Find and place optimal k-groups (k in [2,8]) using DP for sustainability
    2. Greedily place remaining plants by extending clusters or creating new ones
    """

    def __init__(self, garden: Garden, varieties: list[PlantVariety], params: dict | None = None):
        super().__init__(garden, varieties)
        self.params = params or self._get_default_params()
        self._species_nutrient_map = {
            Species.RHODODENDRON: Micronutrient.R,
            Species.GERANIUM: Micronutrient.G,
            Species.BEGONIA: Micronutrient.B,
        }

    def _get_default_params(self) -> dict:
        return {
            'min_sufficiency_weight': 15.0,  # Increased - sustainability is critical
            'species_bonus_weight': 12.0,
            'growth_efficiency_weight': 3.0,
            'base_score_weight': 1.0,
            'exchange_potential_weight': 1.0,
            'species_bonus_all': 25.0,  # Higher bonus for all 3 species
            'species_bonus_two': 8.0,
            'balance_penalty_multiplier': 2.0,
            'cross_species_weight': 15.0,  # Higher - interactions are key
            'optimal_distance_weight': 2.0,
            'min_distance_weight': 1.0,
            'radius_weight': 2.0,  # Higher - larger plants = more growth
            'partner_penalty_multiplier': 1.5,
        }

    def _generate_hexagonal_grid(
        self, grid_spacing: float, max_positions: int = 500
    ) -> list[Position]:
        """Generate hexagonal grid for efficient packing."""
        positions = []
        hex_height = grid_spacing * math.sqrt(3) / 2

        y = 0
        row = 0
        while y <= self.garden.height and len(positions) < max_positions:
            x_offset = (grid_spacing / 2) if row % 2 == 1 else 0
            x = x_offset

            while x <= self.garden.width and len(positions) < max_positions:
                pos = Position(x, y)
                if self.garden.within_bounds(pos):
                    positions.append(pos)
                x += grid_spacing

            y += hex_height
            row += 1

        return positions

    def _generate_square_grid(
        self, grid_spacing: float, max_positions: int = 500
    ) -> list[Position]:
        """Generate square grid for alternative packing pattern."""
        positions = []

        y = 0
        while y <= self.garden.height and len(positions) < max_positions:
            x = 0
            while x <= self.garden.width and len(positions) < max_positions:
                pos = Position(x, y)
                if self.garden.within_bounds(pos):
                    positions.append(pos)
                x += grid_spacing
            y += grid_spacing

        return positions

    def _evaluate_group_sustainability(self, group: list[PlantVariety]) -> float:
        """
        Evaluate how sustainable and growth-capable a group is.

        Key factors from problem statement:
        - Growth requires 2*radius of EACH nutrient per plant
        - Must have all 3 species for exchanges
        - Net production must exceed consumption
        - Balanced production across R, G, B
        """
        if not group:
            return 0.0

        # Calculate total nutrient production
        total_r = sum(v.nutrient_coefficients[Micronutrient.R] for v in group)
        total_g = sum(v.nutrient_coefficients[Micronutrient.G] for v in group)
        total_b = sum(v.nutrient_coefficients[Micronutrient.B] for v in group)

        # Calculate growth requirements: each plant needs 2*radius of each nutrient
        total_requirement = sum(2 * v.radius for v in group)

        # SUSTAINABILITY CHECK: Can production sustain continuous growth?
        if total_requirement > 0:
            r_sufficiency = total_r / total_requirement
            g_sufficiency = total_g / total_requirement
            b_sufficiency = total_b / total_requirement
            # Bottleneck is the minimum
            min_sufficiency = min(r_sufficiency, g_sufficiency, b_sufficiency)
        else:
            min_sufficiency = 0.0

        # SPECIES DIVERSITY: Must have all 3 for exchanges
        species_set = {v.species for v in group}
        if len(species_set) == 3:
            species_bonus = self.params['species_bonus_all']
        elif len(species_set) == 2:
            species_bonus = self.params['species_bonus_two']
        else:
            species_bonus = 0.0  # Can't exchange effectively

        # NET PRODUCTION: Higher is better
        net_production = total_r + total_g + total_b

        # BALANCE: Penalize imbalance (one nutrient too low blocks growth)
        mean = net_production / 3
        variance = ((total_r - mean) ** 2 + (total_g - mean) ** 2 + (total_b - mean) ** 2) / 3
        balance_penalty = math.sqrt(variance) * self.params['balance_penalty_multiplier']

        # GROWTH POTENTIAL: Sum of max sizes (100*r^2 for each plant)
        max_growth_potential = sum(100 * v.radius**2 for v in group)

        # EXCHANGE COMPATIBILITY: Different species can exchange
        exchange_pairs = sum(
            1 for i, v1 in enumerate(group) for v2 in group[i + 1 :] if v1.species != v2.species
        )

        # COMBINED SCORE
        score = (
            min_sufficiency * self.params['min_sufficiency_weight']  # Sustainability (critical!)
            + species_bonus * self.params['species_bonus_weight']  # Diversity
            + (net_production - balance_penalty) * self.params['base_score_weight']  # Production
            + max_growth_potential * 0.01  # Growth potential
            + exchange_pairs * self.params['exchange_potential_weight']  # Exchange potential
        )

        return score

    def _find_best_k_groups_dp(self) -> tuple[int, list[list[PlantVariety]]]:
        """
        Find optimal k (in [2,8]) and corresponding groups using DP.

        Returns: (best_k, best_groups)
        """
        n = len(self.varieties)

        if n <= 2:
            return (n, [self.varieties])

        best_k = 3  # Default
        best_groups = []
        best_score = float('-inf')

        # Test each k in [2, 8]
        for k in range(2, min(9, n + 1)):
            groups = self._greedy_grouping_fast(k)

            # Evaluate this grouping
            total_score = sum(self._evaluate_group_sustainability(g) for g in groups)

            # Bonus for using more plants (less waste)
            plants_used = sum(len(g) for g in groups)
            coverage = plants_used / n
            total_score *= coverage

            # Bonus for having all species represented
            all_species = set()
            for g in groups:
                for v in g:
                    all_species.add(v.species)
            if len(all_species) == 3:
                total_score += 20.0

            if total_score > best_score:
                best_score = total_score
                best_k = k
                best_groups = groups

        return (best_k, best_groups)

    def _greedy_grouping_fast(self, k: int) -> list[list[PlantVariety]]:
        """
        Fast greedy grouping (CRITICAL: avoid exponential search!).
        Always ensures species diversity.
        """
        groups = []
        remaining = self.varieties.copy()

        # Pre-sort by species
        species_lists = {Species.RHODODENDRON: [], Species.GERANIUM: [], Species.BEGONIA: []}
        for v in remaining:
            species_lists[v.species].append(v)

        while remaining:
            group = []

            # Priority: get all 3 species first
            for species in [Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA]:
                if species_lists[species] and len(group) < k:
                    plant = species_lists[species].pop(0)
                    group.append(plant)
                    remaining.remove(plant)

            # Fill remaining slots
            while len(group) < k and remaining:
                # Prefer larger radius plants (more growth potential)
                best_plant = max(
                    remaining[: min(20, len(remaining))],
                    key=lambda v: (v.radius, sum(v.nutrient_coefficients.values())),
                )
                group.append(best_plant)
                remaining.remove(best_plant)
                if best_plant in species_lists[best_plant.species]:
                    species_lists[best_plant.species].remove(best_plant)

            if group:
                groups.append(group)
            else:
                break

        return groups

    def _run_phases_on_test_garden(
        self, grid_positions: list[Position]
    ) -> tuple[list[tuple[PlantVariety, Position]], set[int]]:
        """
        Run Phase 1 and Phase 2 on a temporary test garden.
        Returns placements and used variety IDs.
        """
        # Create temporary test garden
        test_garden = Garden(width=self.garden.width, height=self.garden.height)

        # Phase 1: Find optimal k and place initial groups
        best_k, initial_groups = self._find_best_k_groups_dp()
        placements, used_ids = self._place_initial_groups_on_garden(
            initial_groups, grid_positions, test_garden
        )

        # Phase 2: Greedy cluster extension for remaining plants
        remaining_varieties = [v for v in self.varieties if id(v) not in used_ids]
        if remaining_varieties:
            self._greedy_cluster_extension_on_garden(
                remaining_varieties, placements, grid_positions, test_garden
            )

        return (placements, used_ids)

    def _place_initial_groups_on_garden(
        self, groups: list[list[PlantVariety]], grid_positions: list[Position], garden: Garden
    ) -> tuple[list[tuple[PlantVariety, Position]], set[int]]:
        """Place initial k-groups on specified garden."""
        all_placements = []
        used_ids = set()

        for group in groups:
            sorted_group = sorted(group, key=lambda v: v.radius, reverse=True)

            for variety in sorted_group:
                best_pos = None
                best_score = -1

                for pos in grid_positions[: min(200, len(grid_positions))]:
                    if garden.can_place_plant(variety, pos):
                        score = 0.0
                        cross_species = 0

                        recent = (
                            all_placements[-20:] if len(all_placements) > 20 else all_placements
                        )
                        for placed_var, placed_pos in recent:
                            dx = pos.x - placed_pos.x
                            dy = pos.y - placed_pos.y
                            dist = math.sqrt(dx * dx + dy * dy)
                            interaction_dist = variety.radius + placed_var.radius

                            if dist < interaction_dist and variety.species != placed_var.species:
                                cross_species += 1
                                score += 15.0

                        score += variety.radius * 3.0

                        if score > best_score:
                            best_score = score
                            best_pos = pos

                            if cross_species >= 2:
                                break

                if best_pos:
                    garden.add_plant(variety, best_pos)
                    all_placements.append((variety, best_pos))
                    used_ids.add(id(variety))

        return (all_placements, used_ids)

    def _greedy_cluster_extension_on_garden(
        self,
        remaining: list[PlantVariety],
        existing_placements: list[tuple[PlantVariety, Position]],
        grid_positions: list[Position],
        garden: Garden,
    ) -> None:
        """Greedy cluster extension on specified garden."""
        while remaining:
            best_variety = None
            best_pos = None
            best_score = -1

            for variety in remaining[: min(30, len(remaining))]:
                for pos in grid_positions[: min(150, len(grid_positions))]:
                    if garden.can_place_plant(variety, pos):
                        score = 0.0
                        interactions = 0

                        recent = existing_placements[-15:]
                        for placed_var, placed_pos in recent:
                            dx = pos.x - placed_pos.x
                            dy = pos.y - placed_pos.y
                            dist = math.sqrt(dx * dx + dy * dy)
                            interaction_dist = variety.radius + placed_var.radius

                            if dist < interaction_dist and variety.species != placed_var.species:
                                interactions += 1
                                score += 20.0

                        score += variety.radius * 2.0

                        if score > best_score:
                            best_score = score
                            best_variety = variety
                            best_pos = pos

            if len(remaining) >= 3:
                test_group = remaining[:3]
                cluster_score = self._evaluate_group_sustainability(test_group)

                if cluster_score > best_score * 0.8:
                    for pos in grid_positions[:50]:
                        if garden.can_place_plant(test_group[0], pos):
                            best_variety = test_group[0]
                            best_pos = pos
                            best_score = cluster_score
                            break

            if best_variety and best_pos:
                garden.add_plant(best_variety, best_pos)
                existing_placements.append((best_variety, best_pos))
                remaining.remove(best_variety)
            else:
                break

    def _simulate_and_score(self, test_garden: Garden, turns: int = 100) -> float:
        """Run simulation on test garden and return final growth."""
        from core.engine import Engine

        engine = Engine(test_garden)
        engine.run_simulation(turns)
        return test_garden.total_growth()

    def _gap_fill_with_interactions(
        self,
        remaining: list[PlantVariety],
        grid_positions: list[Position],
        time_budget: float = 20.0,
    ) -> None:
        """
        Phase 4: Gap-fill by maximizing cross-species interactions.
        Continues placing plants until time budget exhausted.
        """
        import time

        start_time = time.time()

        while remaining and (time.time() - start_time < time_budget):
            best_variety = None
            best_pos = None
            best_score = -1

            # Try ALL remaining plants, find the one with best position
            for variety in remaining:
                if time.time() - start_time >= time_budget:
                    break

                # Find best position for this specific plant
                for pos in grid_positions:
                    if not self.garden.can_place_plant(variety, pos):
                        continue

                    # Score based on cross-species interactions
                    interaction_count = 0
                    for existing_plant in self.garden.plants:
                        if variety.species == existing_plant.variety.species:
                            continue  # Same species don't interact

                        dx = pos.x - existing_plant.position.x
                        dy = pos.y - existing_plant.position.y
                        distance = math.sqrt(dx * dx + dy * dy)
                        interaction_distance = variety.radius + existing_plant.variety.radius

                        if distance < interaction_distance:
                            interaction_count += 1

                    # Score = interactions * 10 + radius
                    score = interaction_count * 10.0 + variety.radius * 1.0

                    if score > best_score:
                        best_score = score
                        best_variety = variety
                        best_pos = pos

            # Place best plant found this iteration
            if best_variety and best_pos:
                self.garden.add_plant(best_variety, best_pos)
                remaining.remove(best_variety)
            else:
                # No valid position for any remaining plant
                break

    def cultivate_garden(self) -> None:
        """
        Four-phase cultivation:
        1. Find and place optimal k-groups
        2. Greedily extend clusters or create new ones
        3. Multi-grid testing (square vs hexagonal) with actual simulation
        4. Gap-fill remaining plants maximizing interactions
        """
        if not self.varieties:
            return

        # Calculate grid spacing
        min_radius = min(v.radius for v in self.varieties)
        grid_spacing = float(min_radius)

        # PHASE 3: Multi-Grid Selection (Square vs Hexagonal)
        # Test both grids and pick the one with better actual growth

        # Generate Square Grid + fine grid
        square_grid = self._generate_square_grid(grid_spacing, max_positions=400)
        if min_radius == 1 and max(v.radius for v in self.varieties) > 1:
            fine_grid_square = self._generate_square_grid(1.0, max_positions=300)
            existing_square = {(p.x, p.y) for p in square_grid}
            for pos in fine_grid_square:
                if (pos.x, pos.y) not in existing_square:
                    square_grid.append(pos)

        # Generate Hexagonal Grid + fine grid
        hex_grid = self._generate_hexagonal_grid(grid_spacing, max_positions=400)
        if min_radius == 1 and max(v.radius for v in self.varieties) > 1:
            fine_grid_hex = self._generate_hexagonal_grid(1.0, max_positions=300)
            existing_hex = {(p.x, p.y) for p in hex_grid}
            for pos in fine_grid_hex:
                if (pos.x, pos.y) not in existing_hex:
                    hex_grid.append(pos)

        # Test Square Grid
        test_garden_square = Garden(width=self.garden.width, height=self.garden.height)
        placements_square, used_ids_square = self._run_phases_on_test_garden(square_grid)
        # Apply placements to test garden for simulation
        for variety, pos in placements_square:
            test_garden_square.add_plant(variety, pos)
        score_square = self._simulate_and_score(test_garden_square, turns=365)

        # Test Hexagonal Grid
        test_garden_hex = Garden(width=self.garden.width, height=self.garden.height)
        placements_hex, used_ids_hex = self._run_phases_on_test_garden(hex_grid)
        # Apply placements to test garden for simulation
        for variety, pos in placements_hex:
            test_garden_hex.add_plant(variety, pos)
        score_hex = self._simulate_and_score(test_garden_hex, turns=365)

        # Pick winner and apply to actual garden
        if score_square > score_hex:
            winning_placements = placements_square
            winning_used_ids = used_ids_square
            winning_grid = square_grid
        else:
            winning_placements = placements_hex
            winning_used_ids = used_ids_hex
            winning_grid = hex_grid

        # Apply winning placements to actual garden
        for variety, pos in winning_placements:
            self.garden.add_plant(variety, pos)

        # PHASE 4: Gap-Fill with Interaction Maximization
        remaining_varieties = [v for v in self.varieties if id(v) not in winning_used_ids]

        if remaining_varieties:
            self._gap_fill_with_interactions(remaining_varieties, winning_grid, time_budget=20.0)
