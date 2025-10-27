import math

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.point import Position


class Gardener1(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

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
        Evaluate how balanced a group is in terms of nutrient production/consumption.
        Better balance = more sustainable exchanges = better growth.

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

        # Calculate balance score
        # The more balanced (closer to zero net production), the better
        # But we also want positive production overall
        net_production = total_r + total_g + total_b

        # Penalize imbalance (variance from mean)
        mean_nutrient = net_production / 3
        variance = (
            (total_r - mean_nutrient) ** 2
            + (total_g - mean_nutrient) ** 2
            + (total_b - mean_nutrient) ** 2
        ) / 3

        # Reward positive production, penalize imbalance
        balance_score = net_production - math.sqrt(variance)

        return balance_score

    def _find_optimal_groups_dp(self, k: int) -> list[list[PlantVariety]]:
        """
        Use DP to find optimal groups of size k that maximize balance and growth potential.
        Optimized version with better complexity.

        Args:
            k: Size of each group

        Returns:
            List of optimal plant variety groups
        """
        n = len(self.varieties)

        if n <= k:
            # If we don't have enough varieties, return one group
            return [self.varieties]

        # Simplified approach: greedily form balanced groups
        groups = []
        used = set()

        while len(used) < n:
            remaining = [v for i, v in enumerate(self.varieties) if i not in used]

            if not remaining:
                break

            group_size = min(k, len(remaining))

            # Use DP only for current group
            best_score = float('-inf')
            best_group = None

            def find_group(idx: int, count: int, current: list[int],
                        remaining=remaining, group_size=group_size) -> None:
                nonlocal best_score, best_group

                if count == group_size:
                    group = [remaining[i] for i in current]
                    score = self._evaluate_group_balance(group)
                    if score > best_score:
                        best_score = score
                        best_group = current[:]
                    return

                if idx >= len(remaining):
                    return

                # Take current
                current.append(idx)
                find_group(idx + 1, count + 1, current)
                current.pop()

                # Skip current
                find_group(idx + 1, count, current)

            find_group(0, 0, [])

            if best_group:
                group = [remaining[i] for i in best_group]
                groups.append(group)
                # Mark as used
                for variety in group:
                    for i, v in enumerate(self.varieties):
                        if v is variety:
                            used.add(i)
                            break
            else:
                break

        return groups

    def _place_group_on_grid(
        self, group: list[PlantVariety], grid_positions: list[Position], test_garden: Garden
    ) -> list[tuple[PlantVariety, Position]]:
        """
        Try to place a group of plants on the grid in a way that maximizes interactions.

        Args:
            group: List of plant varieties to place
            grid_positions: Available grid positions
            test_garden: Garden instance for testing placement

        Returns:
            List of (variety, position) tuples for successful placements
        """
        placements = []

        # Sort plants by radius (larger first) for better packing
        sorted_group = sorted(group, key=lambda v: v.radius, reverse=True)

        for variety in sorted_group:
            best_position = None
            max_neighbors = -1

            # Try each grid position
            for pos in grid_positions:
                if test_garden.can_place_plant(variety, pos):
                    # Count how many neighbors this position would have
                    neighbor_count = 0
                    for placed_variety, placed_pos in placements:
                        distance = math.sqrt(
                            (pos.x - placed_pos.x) ** 2 + (pos.y - placed_pos.y) ** 2
                        )
                        interaction_distance = variety.radius + placed_variety.radius
                        if (
                            distance < interaction_distance
                            and variety.species != placed_variety.species
                        ):
                            neighbor_count += 1

                    # Prefer positions with more neighbors (more exchanges)
                    if neighbor_count > max_neighbors:
                        max_neighbors = neighbor_count
                        best_position = pos

            if best_position:
                placements.append((variety, best_position))
                # Simulate placement in test garden
                test_garden.add_plant(variety, best_position)

        return placements

    def cultivate_garden(self) -> None:
        """
        Place plants strategically using DP-based grouping and polygonal grid placement.
        """
        # Generate grid of candidate positions with spacing of 1.0
        grid_spacing = 1.0

        grid_positions = self._generate_polygonal_grid(grid_spacing)

        # Try different group sizes
        best_k = 3  # Start with groups of 3 (good for nutrient diversity)

        # Find optimal groups using DP
        groups = self._find_optimal_groups_dp(best_k)

        # Place each group
        for group in groups:
            self._place_group_on_grid(group, grid_positions, self.garden)

            # Actually place in the real garden (already done in _place_group_on_grid)
            # No need to add again since we passed self.garden directly
