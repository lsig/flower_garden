import math
import random
from collections import defaultdict
from itertools import combinations
from itertools import product as variety_product

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position

ClusterData = tuple[list[PlantVariety], list[tuple[PlantVariety, Position]], float]


class Gardener3(Gardener):
    # Grid and placement parameters
    ANCHOR_POINT_STEP = 0.25
    ROTATION_DEGREES = 15
    PLACEMENT_BUFFER = 0.03

    # Performance limits
    MAX_CLUSTERS = 999999
    MAX_TRIAD_PERMUTATIONS = 999999
    MAX_DIAMOND_PERMUTATIONS = 999999

    # Behavior flags
    PREVENT_INTERACTIONS = False

    # Minimum varieties count to restrict garden size for hexagonal placement
    MIN_TOTAL_VARIETIES_COUNT = 24

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.width = int(garden.width)
        self.height = int(garden.height)
        self.species = [s.name for s in Species]

        self.species_varieties = self._init_species_varieties()
        self.variety_counts = {
            name: [v.name for v in varieties].count(name) for name in set(v.name for v in varieties)
        }
        # print(self.species_varieties)
        # print(self.variety_counts)

    def cultivate_garden(self, prevent_interactions: bool = True) -> None:
        # Try hexagonal placements with random fallback
        # If three unique varieties, with all same radius and same count
        if self._check_hexagonal_condition():
            try:
                placements = self._get_hexagonal_placements()
            except Exception as e:
                print(
                    f'Hexagonal placement failed with error: {e}.\nFalling back to random placements.'
                )
                placements = self._get_random_placements()

            for variety, position in placements:
                res = self.garden.add_plant(variety, position)
                if res is None:
                    print(f'Failed to plant {variety} at pos {position}')

        # Otherwise use clustering based approach
        else:
            species_varieties = self.organize_varieties()

            print(f'Total varieties available: {len(self.varieties)}')

            # Get ranked list of triads
            ranked_triads = self.find_best_triad_permutations(species_varieties)

            # Get ranked list of diamonds
            ranked_diamonds = self.find_best_diamond_permutations(species_varieties, ranked_triads)

            # Combine both triads and diamonds into a single ranked list
            all_clusters = []

            if ranked_triads:
                for varieties, coordinates, score in ranked_triads:
                    all_clusters.append((varieties, coordinates, score))

            if ranked_diamonds:
                for varieties, coordinates, score in ranked_diamonds:
                    all_clusters.append((varieties, coordinates, score))

            # Sort the list by score
            all_clusters.sort(key=lambda x: x[2], reverse=True)

            top_clusters = all_clusters[: self.MAX_CLUSTERS]

            print(
                f'\nUsing cluster list: {len(ranked_triads)} triads + {len(ranked_diamonds)} diamonds = {len(all_clusters)} total clusters'
            )
            print(f'Selected top {len(top_clusters)}')

            # Use the combined ranked list for tiling with pre-filtering
            if top_clusters:
                self.tile_cluster_across_garden_with_prefiltering(
                    top_clusters, prevent_interactions=self.PREVENT_INTERACTIONS
                )

    def _check_hexagonal_condition(self) -> bool:
        exactly_three_varieties = len(self.variety_counts) == 3
        equal_counts = all(
            count == list(self.variety_counts.values())[0] for count in self.variety_counts.values()
        )
        equal_radii = all(
            variety.radius == list(self.species_varieties.values())[0][0].radius
            for variety in self.varieties
        )
        return exactly_three_varieties and equal_counts and equal_radii

    ### Hexagonal Placement Methods ###

    def _get_hexagonal_placements(self) -> list:
        """Generate placements in a hexagonal grid pattern."""
        placements = []

        if len(self.varieties) <= self.MIN_TOTAL_VARIETIES_COUNT:
            garden_width, garden_height = self.garden.width // 2, self.garden.height // 2
        else:
            garden_width, garden_height = self.garden.width, self.garden.height
        garden_internal = Garden(garden_width, garden_height)

        n_species = len(self.species)
        offsets = [0.0, 0.5]
        step_size = 1
        variety_indices = {s: 0 for s in self.species}

        # which species to try next for each row
        current_species_by_row = defaultdict(int)

        for y in range(0, self.height + 1, step_size):
            offset = offsets[y % 2]

            for x in self._frange(offset, self.width + 0.1, step_size):
                position = Position(x, y)

                current_species_idx = current_species_by_row[y]
                species_index = (
                    (current_species_idx + 2) % n_species
                    if y % 2 == 1
                    else current_species_idx % n_species
                )
                species_name = self.species[species_index]

                # skip if we've exhausted varieties for this species
                if variety_indices[species_name] >= len(self.species_varieties[species_name]):
                    # advance the index because there's nothing left for this species
                    current_species_by_row[y] = current_species_idx + 1
                    continue

                variety = self.species_varieties[species_name][variety_indices[species_name]]

                if garden_internal.can_place_plant(variety, position):
                    # print(f"Placing {variety.name} at {position}")
                    placements.append((variety, position))
                    garden_internal.add_plant(variety, position)
                    variety_indices[species_name] += 1

                    # advance the index for this row only on successful placement
                    current_species_by_row[y] = current_species_idx + 1

        return placements

    # Taken from random_gardener.py
    def _get_random_placements(self) -> list:
        """Use random placements as fallback strategy."""
        random_placements = []
        for variety in self.varieties:
            x = random.uniform(0, self.garden.width)
            y = random.uniform(0, self.garden.height)

            position = Position(x, y)

            random_placements.append((variety, position))
        return random_placements

    def _init_species_varieties(self) -> dict:
        specs = {}
        for s in self.species:
            specs[s] = [v for v in self.varieties if v.species.name == s]
        return specs

    def _frange(self, start: float, stop: float, step: float):
        while start < stop:
            yield start
            start += step

    ### Clustering Placement Methods ###

    def organize_varieties(self) -> dict[Species, list[PlantVariety]]:
        species_varieties = {}
        for variety in self.varieties:
            if variety.species not in species_varieties:
                species_varieties[variety.species] = []
            species_varieties[variety.species].append(variety)

        return species_varieties

    def calculate_cluster_score(
        self, plant_varieties: list[PlantVariety], coordinates: list[Position]
    ) -> float:
        # Calculate the net production for each nutrient for all plants in cluster
        delta_r_net = sum(plant.nutrient_coefficients[Micronutrient.R] for plant in plant_varieties)
        delta_g_net = sum(plant.nutrient_coefficients[Micronutrient.G] for plant in plant_varieties)
        delta_b_net = sum(plant.nutrient_coefficients[Micronutrient.B] for plant in plant_varieties)

        # Find the bottleneck
        growth_potential = min(delta_r_net, delta_g_net, delta_b_net)

        # Calculate the Area
        x_min = min(
            coords.x - variety.radius
            for variety, coords in zip(plant_varieties, coordinates, strict=False)
        )
        x_max = max(
            coords.x + variety.radius
            for variety, coords in zip(plant_varieties, coordinates, strict=False)
        )
        y_min = min(
            coords.y - variety.radius
            for variety, coords in zip(plant_varieties, coordinates, strict=False)
        )
        y_max = max(
            coords.y + variety.radius
            for variety, coords in zip(plant_varieties, coordinates, strict=False)
        )

        area = (x_max - x_min) * (y_max - y_min)

        # Final Score
        if area == 0:
            return 0.0

        return growth_potential / area

    def find_best_triad_permutations(
        self, species_varieties: dict[Species, list[PlantVariety]]
    ) -> list[ClusterData]:
        species_list = list(species_varieties.keys())
        if len(species_list) < 3:
            print('Not enough species to form a triad')
            return []

        # Create all possible combinations of 3 species (one of each species)
        species_combinations = list(combinations(species_list, 3))

        all_triads = []

        print('Testing triad permutations...')

        for species_triad in species_combinations:
            # Get all varieties for each species in this combination
            species1_varieties = species_varieties[species_triad[0]]
            species2_varieties = species_varieties[species_triad[1]]
            species3_varieties = species_varieties[species_triad[2]]

            # Test all combinations of varieties from the three species
            variety_combinations = list(
                variety_product(species1_varieties, species2_varieties, species3_varieties)
            )

            for triad_varieties in variety_combinations:
                # Calculate optimal coordinates for this triad
                triad_coordinates = self.find_triad_coordinates(triad_varieties, Position(0, 0))
                coordinates = [pos for variety, pos in triad_coordinates]

                # Calculate the score for this triad
                score = self.calculate_cluster_score(triad_varieties, coordinates)

                # Include all triads (including those with negative scores)
                all_triads.append((triad_varieties, triad_coordinates, score))

        # Sort by score (highest first)
        all_triads.sort(key=lambda x: x[2], reverse=True)

        # Filter to ensure each variety ID appears in only one triad
        unique_triads = self.filter_unique_clusters(all_triads)

        # Limit to reasonable number for performance
        top_triads = unique_triads[: self.MAX_TRIAD_PERMUTATIONS]

        print(f'\nFound {len(top_triads)} unique triads')
        if top_triads:
            print(
                f'Best triad: {[f"{v.name}: {v.species.name}" for v in top_triads[0][0]]} | Score: {top_triads[0][2]:.4f}'
            )

        return top_triads

    def find_best_diamond_permutations(
        self, species_varieties: dict[Species, list[PlantVariety]], ranked_triads: list[ClusterData]
    ) -> list[ClusterData]:
        all_diamonds = []

        if not ranked_triads:
            print('No valid triads provided for diamond formation')
            return []

        # Get all species from the triads
        species_in_triads = set()
        for triad_varieties, _, _ in ranked_triads:
            for variety in triad_varieties:
                species_in_triads.add(variety.species)

        # For each triad, try adding one additional variety from each species in the triad
        for triad_varieties, _, _ in ranked_triads:
            # Get the species present in this triad
            triad_species = [variety.species for variety in triad_varieties]

            # Try adding one additional variety from each species in the triad
            for species in triad_species:
                for additional_variety in species_varieties[species]:
                    # Skip if the additional variety instance is already in the triad
                    if additional_variety in triad_varieties:
                        continue

                    # Create diamond: triad varieties + additional variety (no duplicate instances)
                    diamond_varieties = list(triad_varieties) + [additional_variety]

                    # Ensure the two edge circles (P3 and P4) are from the same species

                    if len(diamond_varieties) >= 4:
                        edge_variety_3 = diamond_varieties[2]
                        edge_variety_4 = diamond_varieties[3]

                        # Skip if the edge circles are not from the same species
                        if edge_variety_3.species != edge_variety_4.species:
                            continue

                    # Calculate diamond coordinates
                    diamond_coordinates = self.find_diamond_coordinates(diamond_varieties)

                    # Extract just the coordinates for scoring
                    coordinates = [pos for variety, pos in diamond_coordinates]

                    # Calculate the score for this diamond
                    score = self.calculate_cluster_score(diamond_varieties, coordinates)

                    all_diamonds.append((diamond_varieties, diamond_coordinates, score))

        # Sort by score
        all_diamonds.sort(key=lambda x: x[2], reverse=True)

        # Filter to ensure each variety ID appears in only one diamond
        unique_diamonds = self.filter_unique_clusters(all_diamonds)

        # Limit to reasonable number for performance
        top_diamonds = unique_diamonds[: self.MAX_DIAMOND_PERMUTATIONS]

        print(f'\nFound {len(top_diamonds)} unique diamonds')
        if top_diamonds:
            print(
                f'Best diamond: {[f"{v.name}: {v.species.name}" for v in top_diamonds[0][0]]} | Score: {top_diamonds[0][2]:.4f}'
            )

        return top_diamonds

    def calculate_optimal_distance(self, radius1: float, radius2: float) -> float:
        return max(radius1, radius2) + self.PLACEMENT_BUFFER

    def filter_unique_clusters(self, clusters: list[ClusterData]) -> list[ClusterData]:
        used_variety_ids = set()
        unique_clusters = []

        for varieties, coordinates, score in clusters:
            variety_ids = {id(variety) for variety in varieties}
            if not (variety_ids & used_variety_ids):
                unique_clusters.append((varieties, coordinates, score))
                used_variety_ids.update(variety_ids)

        return unique_clusters

    def find_diamond_coordinates(
        self, diamond: list[PlantVariety], offset: Position | None = None
    ) -> list[tuple[PlantVariety, Position]]:
        if offset is None:
            offset = Position(0, 0)

        if len(diamond) != 4:
            raise ValueError('Diamond must contain exactly 4 plant varieties')

        variety1, variety2, variety3, variety4 = diamond

        r1 = variety1.radius  # Center circle 1
        r2 = variety2.radius  # Center circle 2
        r3 = variety3.radius  # Edge circle 3
        r4 = variety4.radius  # Edge circle 4

        # Calculate the 5 required distances
        d12 = self.calculate_optimal_distance(r1, r2)  # Distance between the two centers
        d13 = self.calculate_optimal_distance(r1, r3)  # Side 1 of the first triad
        d23 = self.calculate_optimal_distance(r2, r3)  # Side 2 of the first triad
        d14 = self.calculate_optimal_distance(r1, r4)  # Side 1 of the second triad
        d24 = self.calculate_optimal_distance(r2, r4)  # Side 2 of the second triad

        # Place the first two points
        p1 = Position(offset.x, offset.y)
        p2 = Position(offset.x + d12, offset.y)

        # Solve for P3
        x3 = (d12**2 + d13**2 - d23**2) / (2 * d12)
        y3 = math.sqrt(d13**2 - x3**2)
        p3 = Position(offset.x + x3, offset.y + y3)

        # Solve for P4
        x4 = (d12**2 + d14**2 - d24**2) / (2 * d12)
        y4 = -math.sqrt(d14**2 - x4**2)
        p4 = Position(offset.x + x4, offset.y + y4)

        return [(variety1, p1), (variety2, p2), (variety3, p3), (variety4, p4)]

    def find_triad_coordinates(
        self, triad: list[PlantVariety], offset: Position | None = None
    ) -> list[tuple[PlantVariety, Position]]:
        if offset is None:
            offset = Position(0, 0)

        if len(triad) != 3:
            raise ValueError('Triad must contain exactly 3 plant varieties')

        variety1, variety2, variety3 = triad

        # Calculate the triangle's side lengths
        d12 = self.calculate_optimal_distance(
            variety1.radius, variety2.radius
        )  # Distance between variety1 and variety2
        d13 = self.calculate_optimal_distance(
            variety1.radius, variety3.radius
        )  # Distance between variety1 and variety3
        d23 = self.calculate_optimal_distance(
            variety2.radius, variety3.radius
        )  # Distance between variety2 and variety3

        # Place the first two plants
        p1 = Position(offset.x, offset.y)
        p2 = Position(offset.x + d12, offset.y)

        # Calculate the third plant's coordinates
        x = (d12**2 + d13**2 - d23**2) / (2 * d12)
        y = math.sqrt(d13**2 - x**2)

        # Apply offset to the calculated position
        p3 = Position(offset.x + x, offset.y + y)

        return [(variety1, p1), (variety2, p2), (variety3, p3)]

    def tile_cluster_across_garden_with_prefiltering(
        self, ranked_clusters: list[ClusterData], prevent_interactions: bool | None = None
    ) -> None:
        if not ranked_clusters:
            return

        if prevent_interactions is None:
            prevent_interactions = self.PREVENT_INTERACTIONS

        print(f'Found {len(ranked_clusters)} ranked clusters')
        print(f'Interaction prevention: {"ON" if prevent_interactions else "OFF"}')

        # Initialize placement data structures
        anchor_points = self.generate_anchor_points()
        placed_plants = []
        used_varieties = set()
        total_varieties = len(self.varieties)

        print(f'Generated {len(anchor_points)} anchor points')

        # Group clusters by radius signature
        radius_groups = self.group_clusters_by_radius_signature(ranked_clusters)
        print(f'After radius pattern grouping: {len(radius_groups)} unique patterns')

        # Find best clusters placement
        self.process_cluster_placement(
            radius_groups,
            anchor_points,
            placed_plants,
            used_varieties,
            total_varieties,
            prevent_interactions,
        )

        # Now actually place the plants in the garden
        self.place_plants_in_garden(placed_plants)

        print(f'\nTotal plants placed in garden: {len(self.garden.plants)}')

    def group_clusters_by_radius_signature(
        self, ranked_clusters: list[ClusterData]
    ) -> dict[tuple[float, ...], list[ClusterData]]:
        radius_groups = {}
        for varieties, coordinates, score in ranked_clusters:
            # Create radius signature
            radii = tuple(sorted([v.radius for v in varieties]))
            if radii not in radius_groups:
                radius_groups[radii] = []
            radius_groups[radii].append((varieties, coordinates, score))

        # Sort each group by score
        for radius_signature in radius_groups:
            radius_groups[radius_signature].sort(key=lambda x: x[2], reverse=True)

        return radius_groups

    def process_cluster_placement(
        self,
        radius_groups: dict[tuple[float, ...], list[ClusterData]],
        anchor_points: list[tuple[float, float]],
        placed_plants: list[tuple[float, float, float, PlantVariety]],
        used_varieties: set[int],
        total_varieties: int,
        prevent_interactions: bool,
    ) -> None:
        placement_round = 0

        while radius_groups and anchor_points:
            placement_round += 1
            print(f'\n=== Placement Round {placement_round} ===')

            # Find the best available cluster across all radius groups
            best_cluster, best_radius_signature = self.find_best_available_cluster(
                radius_groups, used_varieties
            )

            if best_cluster is None:
                print("No more clusters available that don't use already-placed varieties")
                break

            varieties, coordinates, score = best_cluster
            print(
                f'Trying best available cluster. Radius pattern: {best_radius_signature} | Score: {score:.4f}'
            )

            # Try to place this cluster
            placement_result = self.try_place_cluster(
                varieties,
                coordinates,
                score,
                anchor_points,
                placed_plants,
                used_varieties,
                total_varieties,
                prevent_interactions,
            )
            if placement_result:
                # Remove anchor points within placed plants
                anchor_points = self.remove_anchor_points(anchor_points, placed_plants)
                print(f'Remaining anchor points: {len(anchor_points)}')

                # Check if all varieties have been placed - early termination
                if len(used_varieties) >= total_varieties:
                    print(f'All {total_varieties} varieties have been placed - terminating early')
                    break
            else:
                # No valid placements for this radius pattern, remove entire radius group
                print(
                    f'Radius pattern {best_radius_signature} has no valid placements - removing entire pattern'
                )
                del radius_groups[best_radius_signature]

            # If no more anchor points, we're done
            if not anchor_points:
                print('No more anchor points available.')
                break

    def find_best_available_cluster(
        self, radius_groups: dict[tuple[float, ...], list[ClusterData]], used_varieties: set[int]
    ) -> tuple[ClusterData | None, tuple[float, ...] | None]:
        best_cluster = None
        best_radius_signature = None

        for radius_signature, clusters in radius_groups.items():
            for varieties, coordinates, score in clusters:
                cluster_variety_ids = {id(variety) for variety in varieties}
                if not (cluster_variety_ids & used_varieties):
                    if best_cluster is None or score > best_cluster[2]:
                        best_cluster = (varieties, coordinates, score)
                        best_radius_signature = radius_signature
                    break

        return best_cluster, best_radius_signature

    def try_place_cluster(
        self,
        varieties: list[PlantVariety],
        coordinates: list[tuple[PlantVariety, Position]],
        score: float,
        anchor_points: list[tuple[float, float]],
        placed_plants: list[tuple[float, float, float, PlantVariety]],
        used_varieties: set[int],
        total_varieties: int,
        prevent_interactions: bool,
    ) -> float | None:
        # Collect all possible placements for this cluster
        possible_placements = []

        # Scan all possible anchor points for this cluster
        for anchor_x, anchor_y in anchor_points:
            # Test rotations for better packing
            for rotation_angle in range(0, 360, self.ROTATION_DEGREES):
                # Rotate the cluster coordinates
                rotated_coordinates = self.rotate_cluster(coordinates, rotation_angle)

                # Test if this rotation can be placed at this anchor point
                if self.can_place_cluster_at_anchor(
                    rotated_coordinates, anchor_x, anchor_y, placed_plants, prevent_interactions
                ):
                    # Calculate area by this clsuter
                    new_circles = []
                    for variety, pos in rotated_coordinates:
                        abs_x = anchor_x + pos.x
                        abs_y = anchor_y + pos.y
                        new_circles.append((abs_x, abs_y, variety.radius))

                    added_area = self.calculate_added_area(
                        [(x, y, r) for x, y, r, _ in placed_plants], new_circles
                    )

                    possible_placements.append(
                        (
                            rotated_coordinates,
                            anchor_x,
                            anchor_y,
                            len(rotated_coordinates),
                            added_area,
                        )
                    )

        # If we found valid placements, choose the best one (added least amount of area)
        if possible_placements:
            # Sort by additonal area added
            possible_placements.sort(key=lambda x: x[4], reverse=False)
            best_placement = possible_placements[0]

            # Place the best placement found
            rotation, x, y, plants, added_area_new = best_placement
            self.place_cluster_at_anchor(rotation, x, y, placed_plants)

            # Mark all varieties in this cluster as used
            for variety in varieties:
                used_varieties.add(id(variety))

            print(
                f'Placed cluster (score: {score:.4f}) at ({x:.1f}, {y:.1f}) - {plants} plants, area increment: {added_area_new:.2f}'
            )
            return added_area_new

        return None

    def generate_anchor_points(self) -> list[tuple[float, float]]:
        """ Generates anchor points hexagonaly """
        # get smallest as they allow denser anchor grids for finer placement control
        min_radius = min(v.radius for v in self.varieties)
        # adaptive steps instead of fixed: use percentage of smallest radius, but at least 0.25
        step = max(0.25, min_radius * 0.4)
        
        anchor_points = []
        y = 0.0
        row = 0
        # go top to bottom
        while y <= self.garden.height:
            # offset odd rows by half step to create hexagonal pattern
            x_offset = (step / 2) if row % 2 == 1 else 0
            x = x_offset
            
            while x <= self.garden.width:
                anchor_points.append((x, y))
                x += step
            
            # hexagonal vertical placing
            y += step * math.sqrt(3) / 2
            row += 1
        
        return anchor_points

    def remove_anchor_points(
        self,
        anchor_points: list[tuple[float, float]],
        placed_plants: list[tuple[float, float, float, PlantVariety]],
    ) -> list[tuple[float, float]]:
        remaining_anchors = []

        for anchor_x_test, anchor_y_test in anchor_points:
            # Check if this anchor point is within any circle of placed plants
            too_close = False
            for plant_x, plant_y, plant_radius, _ in placed_plants:
                # Calculate distance from anchor point to plant center
                distance = ((anchor_x_test - plant_x) ** 2 + (anchor_y_test - plant_y) ** 2) ** 0.5

                # Remove anchor if it's within the plant's radius
                if distance <= plant_radius:
                    too_close = True
                    break

            # Keep anchor point if it's not too close to any plant
            if not too_close:
                remaining_anchors.append((anchor_x_test, anchor_y_test))

        return remaining_anchors

    def can_place_cluster_at_anchor(
        self,
        cluster_coordinates: list[tuple[PlantVariety, Position]],
        anchor_x: float,
        anchor_y: float,
        placed_plants: list[tuple[float, float, float, PlantVariety]],
        prevent_interactions: bool = True,
    ) -> bool:
        # Cluster center bounds
        cluster_min_x = min(anchor_x + pos.x for variety, pos in cluster_coordinates)
        cluster_max_x = max(anchor_x + pos.x for variety, pos in cluster_coordinates)
        cluster_min_y = min(anchor_y + pos.y for variety, pos in cluster_coordinates)
        cluster_max_y = max(anchor_y + pos.y for variety, pos in cluster_coordinates)

        # Check if centers are within bounds
        if (
            cluster_min_x < 0
            or cluster_max_x > self.garden.width
            or cluster_min_y < 0
            or cluster_max_y > self.garden.height
        ):
            return False

        for variety, pos in cluster_coordinates:
            # Calculate absolute coordinates
            x_new = anchor_x + pos.x
            y_new = anchor_y + pos.y
            r_new = variety.radius

            # Check collision with placed plants
            for x_old, y_old, r_old, variety_old in placed_plants:
                # They are too far apart
                dx = abs(x_new - x_old)
                dy = abs(y_new - y_old)
                if dx > r_new + r_old or dy > r_new + r_old:
                    continue

                # Calculate distance between centers
                distance = (dx**2 + dy**2) ** 0.5

                if prevent_interactions:
                    # Check if plants are from different species would interact
                    if variety.species != variety_old.species:
                        # Prevent interactions: distance must be >= sum of radii
                        interaction_distance = r_new + r_old
                        if distance < interaction_distance:
                            return False
                    else:
                        # Same species: just prevent overlap (distance >= max radius)
                        if distance < max(r_new, r_old):
                            return False
                else:
                    # Allow interactions: only prevent overlap (distance >= max radius)
                    if distance < max(r_new, r_old):
                        return False

        return True

    def calculate_added_area(
        self,
        existing_circles: list[tuple[float, float, float]],
        new_circles: list[tuple[float, float, float]],
    ) -> float:
        if not new_circles:
            return 0.0

        # Calculate area of new circles
        new_area = sum(math.pi * r**2 for _, _, r in new_circles)

        # Subtract overlaps between new circles and existing circles
        for x1, y1, r1 in new_circles:
            for x2, y2, r2 in existing_circles:
                overlap = self.calculate_circle_overlap(x1, y1, r1, x2, y2, r2)
                new_area -= overlap

        # Add back overlaps between new circles (they were subtracted twice)
        for i in range(len(new_circles)):
            for j in range(i + 1, len(new_circles)):
                x1, y1, r1 = new_circles[i]
                x2, y2, r2 = new_circles[j]
                overlap = self.calculate_circle_overlap(x1, y1, r1, x2, y2, r2)
                new_area += overlap

        return max(0.0, new_area)

    def calculate_circle_overlap(
        self, x1: float, y1: float, r1: float, x2: float, y2: float, r2: float
    ) -> float:
        # Calculate distance between centers
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Check if circles don't overlap at all
        if distance >= r1 + r2:
            return 0.0

        # Calculate overlap using the circle-circle intersection formula
        a = distance
        R = r1
        r = r2

        # Calculate the intersection area
        term1 = r**2 * math.acos((a**2 + r**2 - R**2) / (2 * a * r))
        term2 = R**2 * math.acos((a**2 + R**2 - r**2) / (2 * a * R))
        term3 = 0.5 * math.sqrt((-a + r + R) * (a + r - R) * (a - r + R) * (a + r + R))

        overlap = term1 + term2 - term3

        return overlap

    def place_cluster_at_anchor(
        self,
        cluster_coordinates: list[tuple[PlantVariety, Position]],
        anchor_x: float,
        anchor_y: float,
        placed_plants: list[tuple[float, float, float, PlantVariety]],
    ) -> None:
        for variety, pos in cluster_coordinates:
            x_new = anchor_x + pos.x
            y_new = anchor_y + pos.y

            # Add to placed plants list
            placed_plants.append((x_new, y_new, variety.radius, variety))

    def place_plants_in_garden(
        self, placed_plants: list[tuple[float, float, float, PlantVariety]]
    ) -> None:
        successful_placements = 0
        failed_placements = 0

        for x, y, _, variety in placed_plants:
            position = Position(x, y)
            result = self.garden.add_plant(variety, position)
            if result:
                successful_placements += 1
            else:
                failed_placements += 1
                print(f"Failed to place variety '{variety.name}' at ({x:.1f}, {y:.1f})")

        print(f'\nFinal placement: {successful_placements} successful, {failed_placements} failed')

    def rotate_cluster(
        self, cluster_coordinates: list[tuple[PlantVariety, Position]], angle_degrees: float
    ) -> list[tuple[PlantVariety, Position]]:
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        rotated = []
        for variety, pos in cluster_coordinates:
            new_x = pos.x * cos_a - pos.y * sin_a
            new_y = pos.x * sin_a + pos.y * cos_a
            rotated.append((variety, Position(new_x, new_y)))

        return rotated
