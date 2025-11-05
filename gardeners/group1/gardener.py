import math

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener1(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety], params: dict | None = None):
        super().__init__(garden, varieties)
        # Default parameters (can be overridden)
        self.params = params or self._get_default_params()

    def _get_default_params(self) -> dict:
        """Default parameter values (empirically tuned for maximum growth)."""
        return {
            # Group evaluation weights (tuned on 25 config files)
            'min_sufficiency_weight': 15.0,  # Growth sustainability (critical)
            'species_bonus_weight': 5.0,  # Species diversity importance
            'growth_efficiency_weight': 2.0,  # Growth efficiency multiplier
            'base_score_weight': 1.0,  # Base production balance
            'exchange_potential_weight': 0.5,  # Exchange compatibility
            'species_bonus_all': 20.0,  # Bonus for having all 3 species
            'species_bonus_two': 5.0,  # Bonus for having 2 species
            'balance_penalty_multiplier': 2.0,  # Penalty for nutrient imbalance
            # Placement weights (tuned on 25 config files)
            'cross_species_weight': 12.0,  # Cross-species exchange importance
            'optimal_distance_weight': 2.5,  # Optimal distance bonus (tuned: was 2.0)
            'min_distance_weight': 1.5,  # Tight packing bonus
            'radius_weight': 1.0,  # Larger plant bonus
            'partner_penalty_multiplier': 2.0,  # Penalty for too many partners
        }

    def _generate_polygonal_grid(self, grid_spacing: float = 1.0) -> list[Position]:
        """
        Generate a polygonal (hexagonal-like) grid of candidate positions.
        Hexagonal packing is more efficient than square grids for circular plants.

        Args:
            grid_spacing: Distance between grid points

        Returns:
            List of Position objects forming a hexagonal grid
        """
        positions = []

        # Hexagonal grid uses offset rows
        # sqrt(3)/2 is around 0.866 is the vertical spacing factor for hex grids
        hex_height = grid_spacing * math.sqrt(3) / 2

        y = 0
        row = 0
        while y <= self.garden.height:
            # Alternate row offset for hexagonal packing
            x_offset = (grid_spacing / 2) if row % 2 == 1 else 0
            x = x_offset

            while x <= self.garden.width:
                pos = Position(x, y)
                if self.garden.within_bounds(pos):
                    positions.append(pos)
                x += grid_spacing

            y += hex_height
            row += 1

        return positions

    def _evaluate_group_balance(self, group: list[PlantVariety]) -> float:
        """
        Optimized evaluation based on project requirements.

        Key insights from problem statement:
        - Plants need 2*radius of EACH nutrient to grow (critical bottleneck)
        - Exchange offers are split among partners (fewer partners = larger exchanges)
        - Only different species can exchange (must have all 3 species)
        - Net production must be positive but balanced across nutrients

        Args:
            group: List of plant varieties

        Returns:
            Score representing group quality (higher is better)
        """
        if not group:
            return 0.0

        # Sum up all nutrient coefficients
        total_r = sum(v.nutrient_coefficients[Micronutrient.R] for v in group)
        total_g = sum(v.nutrient_coefficients[Micronutrient.G] for v in group)
        total_b = sum(v.nutrient_coefficients[Micronutrient.B] for v in group)

        # CRITICAL: Growth requires 2*radius of EACH nutrient
        # Calculate total growth requirement per turn
        total_growth_req_r = sum(2 * v.radius for v in group)
        total_growth_req_g = sum(2 * v.radius for v in group)
        total_growth_req_b = sum(2 * v.radius for v in group)

        # Calculate net production per turn
        net_production = total_r + total_g + total_b

        # CRITICAL METRIC: Can this group sustain growth?
        # We need production to exceed or match growth requirements
        # But we need BALANCED production (each nutrient must be sufficient)
        r_sufficiency = total_r / total_growth_req_r if total_growth_req_r > 0 else 0
        g_sufficiency = total_g / total_growth_req_g if total_growth_req_g > 0 else 0
        b_sufficiency = total_b / total_growth_req_b if total_growth_req_b > 0 else 0

        # Minimum sufficiency (bottleneck) - this is the limiting factor
        min_sufficiency = min(r_sufficiency, g_sufficiency, b_sufficiency)

        # Balance score: reward balanced production
        # Penalize imbalance more heavily (variance from mean)
        mean_production = net_production / 3
        variance = (
            (total_r - mean_production) ** 2
            + (total_g - mean_production) ** 2
            + (total_b - mean_production) ** 2
        ) / 3
        balance_penalty = math.sqrt(variance)

        # Base score: positive net production with balanced nutrients
        base_score = net_production - balance_penalty * self.params['balance_penalty_multiplier']

        # CRITICAL: Species diversity - MUST have all 3 species for exchanges
        species_set = {v.species for v in group}
        if len(species_set) == 3:
            species_bonus = self.params['species_bonus_all']
        elif len(species_set) == 2:
            species_bonus = self.params['species_bonus_two']
        else:
            species_bonus = 0.0  # No exchanges possible

        # Growth efficiency: how well production matches growth needs
        # Reward groups where production can sustain continuous growth
        growth_efficiency = min_sufficiency * 10.0  # Scale up for visibility

        # Exchange potential: calculate how well plants can exchange
        # Ideal: Each plant pairs with complementary species
        exchange_potential = 0.0
        for i, v1 in enumerate(group):
            for v2 in group[i + 1 :]:
                if v1.species != v2.species:
                    # Calculate exchange compatibility
                    # One produces what the other needs
                    # Manual species->nutrient mapping
                    if v1.species == Species.RHODODENDRON:
                        prod1 = Micronutrient.R
                    elif v1.species == Species.GERANIUM:
                        prod1 = Micronutrient.G
                    else:  # BEGONIA
                        prod1 = Micronutrient.B

                    if v2.species == Species.RHODODENDRON:
                        prod2 = Micronutrient.R
                    elif v2.species == Species.GERANIUM:
                        prod2 = Micronutrient.G
                    else:
                        prod2 = Micronutrient.B

                    # Reward if they produce different nutrients (can exchange)
                    if prod1 != prod2:
                        # Calculate how much they can exchange
                        # Based on production coefficients
                        coef1 = v1.nutrient_coefficients[prod1]
                        coef2 = v2.nutrient_coefficients[prod2]
                        exchange_potential += coef1 * coef2  # Reward high production pairs

        # Combined score prioritizing critical factors
        final_score = (
            base_score * self.params['base_score_weight']
            + species_bonus * self.params['species_bonus_weight']
            + growth_efficiency * self.params['growth_efficiency_weight']
            + exchange_potential * self.params['exchange_potential_weight']
            + min_sufficiency * self.params['min_sufficiency_weight']
        )

        return final_score

    def _find_optimal_groups_dp(self, k: int) -> list[list[PlantVariety]]:
        """
        Find optimal groups using greedy approach for scalability.

        For large numbers of varieties (100+), uses fast greedy clustering.
        For smaller sets (< 50), uses limited combinatorial search.

        Args:
            k: Size of each group

        Returns:
            List of optimal plant variety groups
        """
        n = len(self.varieties)

        if n <= k:
            return [self.varieties]

        # For large sets, use fast greedy approach
        if n > 50:
            return self._greedy_grouping(k)

        # For smaller sets, use limited combinatorial search
        return self._limited_search_grouping(k)

    def _greedy_grouping(self, k: int) -> list[list[PlantVariety]]:
        """Fast greedy grouping for large numbers of varieties."""
        groups = []
        remaining = self.varieties.copy()

        # Group varieties by species for better diversity
        species_groups = {Species.RHODODENDRON: [], Species.GERANIUM: [], Species.BEGONIA: []}
        for v in remaining:
            species_groups[v.species].append(v)

        while remaining:
            group = []

            # Try to ensure species diversity: take one from each species if available
            for species in [Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA]:
                if species_groups[species] and len(group) < k:
                    group.append(species_groups[species].pop(0))
                    remaining.remove(group[-1])

            # Fill remaining slots with best matches
            while len(group) < k and remaining:
                best_v = None
                best_score = float('-inf')

                for v in remaining[: min(50, len(remaining))]:  # Limit search for speed
                    test_group = group + [v]
                    score = self._evaluate_group_balance(test_group)
                    if score > best_score:
                        best_score = score
                        best_v = v

                if best_v:
                    group.append(best_v)
                    remaining.remove(best_v)
                    if best_v in species_groups[best_v.species]:
                        species_groups[best_v.species].remove(best_v)
                else:
                    break

            if group:
                groups.append(group)
            else:
                break

        return groups

    def _limited_search_grouping(self, k: int) -> list[list[PlantVariety]]:
        """Limited combinatorial search for smaller sets."""
        groups = []
        used = set()

        while len(used) < len(self.varieties):
            remaining = [v for i, v in enumerate(self.varieties) if i not in used]

            if not remaining:
                break

            group_size = min(k, len(remaining))

            # Limit search space: only try combinations from first 30 remaining
            search_space = remaining[: min(30, len(remaining))]

            best_score = float('-inf')
            best_group = None

            def find_group(
                idx: int, count: int, current: list[int], space=search_space, size=group_size
            ) -> None:
                nonlocal best_score, best_group

                if count == size:
                    group = [space[i] for i in current]
                    score = self._evaluate_group_balance(group)
                    if score > best_score:
                        best_score = score
                        best_group = current[:]
                    return

                if idx >= len(space):
                    return

                # Take current
                current.append(idx)
                find_group(idx + 1, count + 1, current, space, size)
                current.pop()

                # Skip current
                find_group(idx + 1, count, current, space, size)

            find_group(0, 0, [])

            if best_group:
                group = [search_space[i] for i in best_group]
                groups.append(group)
                # Mark as used
                for variety in group:
                    for i, v in enumerate(self.varieties):
                        if v is variety:
                            used.add(i)
                            break
            else:
                # Fallback: take first k remaining
                if remaining:
                    groups.append(remaining[:group_size])
                break

        return groups

    def _place_group_on_grid(
        self, group: list[PlantVariety], grid_positions: list[Position], test_garden: Garden
    ) -> list[tuple[PlantVariety, Position]]:
        """
        Enhanced placement strategy that maximizes exchange opportunities.

        Improvements:
        - Prioritizes high-radius plants (more growth potential)
        - Creates optimal interaction distances for exchanges
        - Prefers positions that enable multiple cross-species interactions
        - Considers exchange network value (hub creation)

        Args:
            group: List of plant varieties to place
            grid_positions: Available grid positions
            test_garden: Garden instance for testing placement

        Returns:
            List of (variety, position) tuples for successful placements
        """
        placements = []

        # Sort plants by radius (larger first) for better packing and growth potential
        # Also prioritize by production coefficient (more productive first)
        sorted_group = sorted(
            group,
            key=lambda v: (
                v.radius,  # Primary: larger radius = more growth
                max(v.nutrient_coefficients.values()),  # Secondary: higher production
            ),
            reverse=True,
        )

        for variety in sorted_group:
            best_position = None
            best_score = -1
            packing_score = -1  # Track best packing-only score as fallback

            # Try each grid position
            for pos in grid_positions:
                if test_garden.can_place_plant(variety, pos):
                    score = 0.0
                    packing_only_score = 0.0
                    interaction_count = 0
                    cross_species_count = 0
                    optimal_distance_bonus = 0.0
                    min_distance_bonus = 0.0  # Bonus for tight packing

                    # Evaluate interactions with already placed plants
                    for placed_variety, placed_pos in placements:
                        distance = math.sqrt(
                            (pos.x - placed_pos.x) ** 2 + (pos.y - placed_pos.y) ** 2
                        )
                        min_required_distance = max(variety.radius, placed_variety.radius)
                        interaction_distance = variety.radius + placed_variety.radius

                        # PACKING OPTIMIZATION: Bonus for perfect packing (exact minimum distance)
                        # This maximizes garden capacity with 100% packing efficiency
                        if distance >= min_required_distance:
                            # Bonus only for exact minimum distance (perfect packing)
                            distance_ratio = (
                                distance / min_required_distance if min_required_distance > 0 else 0
                            )
                            # Only reward exact minimum (1.0) for perfect packing
                            if abs(distance_ratio - 1.0) < 0.01:  # Exactly at minimum (with small tolerance for floating point)
                                min_distance_bonus += 3.0  # Maximum bonus for perfect packing
                            packing_only_score += min_distance_bonus

                        # Check if within interaction range for exchanges
                        if distance < interaction_distance:
                            interaction_count += 1

                            # Cross-species interactions are more valuable
                            if variety.species != placed_variety.species:
                                cross_species_count += 1

                                # CRITICAL: Optimal distance for exchanges
                                # Place at ~90% of max interaction distance for efficiency
                                optimal_ratio = (
                                    distance / interaction_distance
                                    if interaction_distance > 0
                                    else 0
                                )
                                if 0.85 <= optimal_ratio <= 0.95:
                                    optimal_distance_bonus += 3.0  # Perfect positioning
                                elif 0.75 <= optimal_ratio < 0.85:
                                    optimal_distance_bonus += 1.5
                                elif 0.7 <= optimal_ratio < 0.75:
                                    optimal_distance_bonus += 0.5

                                # Bonus for complementary exchanges
                                nutrient1 = variety.nutrient_coefficients
                                nutrient2 = placed_variety.nutrient_coefficients

                                # Reward if one produces what the other needs
                                for nut in Micronutrient:
                                    if (nutrient1[nut] > 0 and nutrient2[nut] < 0) or (
                                        nutrient1[nut] < 0 and nutrient2[nut] > 0
                                    ):
                                        optimal_distance_bonus += 1.0

                    # Score calculation: balance packing density with exchanges
                    # KEY INSIGHT: For large gardens, packing first is critical
                    partner_penalty = (
                        max(
                            0, (cross_species_count - 3) * self.params['partner_penalty_multiplier']
                        )
                        if cross_species_count > 3
                        else 0
                    )

                    # Combined score: prioritize exchanges when possible, but also reward packing
                    score = (
                        cross_species_count * self.params['cross_species_weight']
                        + optimal_distance_bonus * self.params['optimal_distance_weight']
                        + min_distance_bonus * self.params['min_distance_weight']
                        + (variety.radius * self.params['radius_weight'])
                        - partner_penalty  # Penalty for too many partners
                    )

                    # Packing-only score (for when no exchanges available)
                    packing_only_score = min_distance_bonus + interaction_count * 0.5

                    # Always consider both scores, but prioritize exchanges when available
                    if cross_species_count > 0:
                        # We have exchanges - use combined score
                        if score > best_score:
                            best_score = score
                            best_position = pos
                    else:
                        # No exchanges - prioritize tight packing
                        if packing_only_score > packing_score:
                            packing_score = packing_only_score
                            best_position = pos
                            best_score = packing_only_score  # Use packing score as main score

            if best_position:
                placements.append((variety, best_position))
                # Simulate placement in test garden
                test_garden.add_plant(variety, best_position)

        return placements

    def cultivate_garden(self) -> None:
        """
        Enhanced cultivation strategy that maximizes growth.

        Improvements:
        - Dynamic grid spacing based on plant radii
        - Tests multiple group sizes and selects best
        - Prioritizes high-value plants (larger radius, better production)
        """
        # Calculate optimal grid spacing for perfect packing
        # Key insight: Use exact minimum radius to maximize density
        # Plants only need distance >= max(r1, r2), so we can pack at exact minimum
        if self.varieties:
            min_radius = min(v.radius for v in self.varieties)

            # Use exact minimum radius for perfect 100% packing
            # This allows plants to be placed at exactly minimum distance
            grid_spacing = float(min_radius)  # Exact minimum for perfect packing
        else:
            grid_spacing = 1.0

        # Generate primary grid
        grid_positions = self._generate_polygonal_grid(grid_spacing)

        # For mixed radii, add a finer secondary grid for small plants
        if self.varieties:
            min_radius = min(v.radius for v in self.varieties)
            max_radius = max(v.radius for v in self.varieties)
            if min_radius < max_radius and min_radius == 1:
                # Add finer grid for radius 1 plants when mixed with larger ones
                # Use exact minimum for perfect packing
                fine_grid = self._generate_polygonal_grid(1.0)
                # Combine grids (remove duplicates)
                existing_positions = {(p.x, p.y) for p in grid_positions}
                for pos in fine_grid:
                    if (pos.x, pos.y) not in existing_positions:
                        grid_positions.append(pos)

        # Try multiple group sizes and select the best configuration
        # Group sizes to try: 3 (all species), 4-6 (more exchanges), and larger if needed
        n_varieties = len(self.varieties)

        # For large sets, limit group size testing to avoid timeout
        if n_varieties > 100:
            candidate_group_sizes = [3, 4]  # Only test essential sizes
        elif n_varieties > 50:
            candidate_group_sizes = [3, 4, 5]
        else:
            candidate_group_sizes = [3, 4, 5, 6]
            if n_varieties > 12:
                candidate_group_sizes.extend([7, 8])

        best_groups = None
        best_total_score = float('-inf')

        # Evaluate each group size
        for k in candidate_group_sizes:
            if k > len(self.varieties):
                continue

            groups = self._find_optimal_groups_dp(k)

            # Evaluate the grouping quality
            total_score = sum(self._evaluate_group_balance(group) for group in groups)

            # Bonus for having all 3 species represented across groups
            all_species = set()
            for group in groups:
                for v in group:
                    all_species.add(v.species)

            if len(all_species) == 3:
                total_score += 10.0  # Bonus for having all species

            # Prefer configurations that use more plants (less waste)
            coverage_ratio = sum(len(g) for g in groups) / len(self.varieties)
            total_score *= coverage_ratio

            if total_score > best_total_score:
                best_total_score = total_score
                best_groups = groups

        # Fallback if no groups found
        if not best_groups:
            # Try with minimum group size
            best_groups = (
                self._find_optimal_groups_dp(3) if len(self.varieties) >= 3 else [self.varieties]
            )

        # Place each group
        for group in best_groups:
            self._place_group_on_grid(group, grid_positions, self.garden)
