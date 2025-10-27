"""Greedy Planting Algorithm Implementation."""

import os
from collections import defaultdict

import yaml

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.point import Position
from gardeners.group10.greedy_planting_algorithm_1026.utils import (
    calculate_distance,
    circle_circle_intersection,
    evaluate_placement,
    filter_candidates,
    generate_geometric_candidates,
    geometric_heuristic,
    simulate_and_score,
)


class GreedyGardener(Gardener):
    """Greedy planting algorithm with geometric candidate generation and nutrient balancing."""

    def __init__(
        self, garden: Garden, varieties: list[PlantVariety], simulation_turns: int | None = None
    ):
        super().__init__(garden, varieties)
        self.config = self._load_config()

        # Use min(simulation_turns, config_T) if simulation_turns provided
        # This allows T in config to be a maximum, with actual turns passed at runtime
        if simulation_turns is not None:
            self.config['simulation']['T'] = min(simulation_turns, self.config['simulation']['T'])

        self.current_score = 0.0
        self.remaining_varieties = varieties.copy()

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

        with open(config_path) as f:
            config = yaml.safe_load(f)

        return config

    def cultivate_garden(self) -> None:
        """
        Main placement loop: iteratively place plants using greedy selection.
        """
        iteration = 0

        if self.config['debug']['verbose']:
            print(f'Starting placement with {len(self.remaining_varieties)} varieties')

        while self.remaining_varieties:
            iteration += 1

            if self.config['debug']['verbose']:
                constraints = []
                if len(self.garden.plants) < 3:
                    constraints.append('different species')
                if len(self.garden.plants) >= 2:
                    constraints.append('2-species interaction')
                constraint_str = f' [{", ".join(constraints)}]' if constraints else ''
                print(
                    f'Iter {iteration}: {len(self.garden.plants)} placed, {len(self.remaining_varieties)} remain{constraint_str}'
                )

            # Generate candidate positions
            candidates = self._generate_candidates()

            if not candidates:
                if self.config['debug']['verbose']:
                    print('No valid candidates found. Stopping.')
                break

            if self.config['debug']['log_candidates']:
                print(f'Generated {len(candidates)} candidates')

            # Find best (variety, position) pair
            best_value, best_variety, best_position = self._find_best_placement(candidates)

            # Check stopping criterion
            epsilon = self.config['placement']['epsilon']
            if best_value <= epsilon:
                if self.config['debug']['verbose']:
                    print(f'Best value {best_value:.4f} <= epsilon {epsilon}. Stopping.')
                break

            # Place the plant
            plant = self.garden.add_plant(best_variety, best_position)

            if plant is None:
                if self.config['debug']['verbose']:
                    print(
                        f'Failed to place {best_variety.name} at ({best_position.x:.2f}, {best_position.y:.2f})'
                    )
                self.remaining_varieties.remove(best_variety)
                continue

            # Update state
            self.remaining_varieties.remove(best_variety)
            self.current_score = simulate_and_score(
                self.garden,
                self.config['simulation']['T'],
                self.config['simulation']['w_short'],
                self.config['simulation']['w_long'],
            )

            if self.config['debug']['verbose']:
                print(
                    f'  → {best_variety.species.name[0]} at ({int(best_position.x)},{int(best_position.y)}): value={best_value:.2f}, score={self.current_score:.2f}'
                )

        if self.config['debug']['verbose']:
            print('\n=== Placement Complete ===')
            print(f'Total plants placed: {len(self.garden.plants)}')
            print(f'Final score: {self.current_score:.4f}')
            # Note: Analysis not shown here - plants haven't grown yet (size=0)
            # Call print_final_analysis() after simulation for meaningful results

    def print_final_analysis(self) -> None:
        """Print detailed analysis of the final garden layout."""
        from collections import defaultdict

        from core.plants.species import Species

        if len(self.garden.plants) == 0:
            print('\nNo plants placed.')
            return

        # Analyze results by species
        species_stats = defaultdict(
            lambda: {'count': 0, 'total_growth': 0.0, 'sizes': [], 'interactions': []}
        )

        for plant in self.garden.plants:
            species = plant.variety.species
            interactions = self.garden.get_interacting_plants(plant)
            species_stats[species]['count'] += 1
            species_stats[species]['total_growth'] += plant.size
            species_stats[species]['sizes'].append(plant.size)
            species_stats[species]['interactions'].append(len(interactions))

        # Species breakdown
        print(f'\n{"Species Analysis":-^60}')
        for species in [Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA]:
            if species in species_stats:
                stats = species_stats[species]
                avg_size = stats['total_growth'] / stats['count']
                avg_interactions = sum(stats['interactions']) / stats['count']
                max_size = max(stats['sizes'])
                min_size = min(stats['sizes'])

                print(f'\n{species.name}:')
                print(f'  Count:         {stats["count"]}')
                print(f'  Total Growth:  {stats["total_growth"]:.2f}')
                print(f'  Average Size:  {avg_size:.2f}')
                print(f'  Size Range:    {min_size:.1f} - {max_size:.1f}')
                print(f'  Avg Interact:  {avg_interactions:.1f} partners')

        # Individual plant details
        print(f'\n{"Individual Plants":-^60}')
        for i, plant in enumerate(self.garden.plants, 1):
            growth_pct = plant.growth_percentage()
            interactions = self.garden.get_interacting_plants(plant)
            species_letter = plant.variety.species.name[0]

            # Count interactions by species
            interaction_species = {}
            for partner in interactions:
                s = partner.variety.species.name[0]
                interaction_species[s] = interaction_species.get(s, 0) + 1
            interact_str = ', '.join(
                f'{count}{s}' for s, count in sorted(interaction_species.items())
            )

            print(
                f'{i:2}. {species_letter} pos=({plant.position.x:2.0f},{plant.position.y:2.0f}) '
                f'size={plant.size:5.1f} ({growth_pct:4.1f}%) '
                f'partners=[{interact_str}]'
            )

    def _generate_candidates(self) -> list[Position]:
        """Generate candidate positions based on current garden state."""
        if len(self.garden.plants) == 0:
            # First plant: use fixed starting point (center of garden)
            # Rationale: Without any existing plants, all positions are equivalent
            # for the first plant. Starting at the center provides:
            # 1. Maximum space for subsequent placements in all directions
            # 2. 50× speedup vs. grid sampling (1 vs 50+ positions)
            # 3. Deterministic behavior
            center_x = int(self.garden.width / 2)
            center_y = int(self.garden.height / 2)
            candidates = [Position(x=center_x, y=center_y)]
        elif len(self.garden.plants) >= 2:
            # 3rd plant onwards: prioritize multi-species interaction zones
            # Try to generate multi-species candidates for each species type
            candidates = []
            species_tried = set()

            for variety in self.remaining_varieties:
                if variety.species not in species_tried:
                    species_tried.add(variety.species)
                    multi_candidates = self._generate_multi_species_candidates(variety)
                    candidates.extend(multi_candidates)

            # Always add standard geometric candidates as fallback
            representative_variety = self.remaining_varieties[0]
            standard_candidates = generate_geometric_candidates(
                self.garden,
                representative_variety,
                self.config['geometry']['angle_samples'],
                self.config['geometry']['max_anchor_pairs'],
            )
            candidates.extend(standard_candidates)
        else:
            # 2nd plant: prioritize horizontal right placement
            # Generate candidates to the right of the first plant
            first_plant = self.garden.plants[0]
            representative_variety = self.remaining_varieties[0]

            candidates = []
            # Generate candidates at various distances to the right
            r_first = first_plant.variety.radius
            r_new = representative_variety.radius

            # System allows: distance >= max(r1, r2) for placement
            # Interaction requires: distance < r1 + r2
            # So valid interaction range: [max(r1, r2), r1 + r2)
            min_distance = max(r_first, r_new)
            interaction_distance = r_first + r_new

            # Try distances from min_distance to just under interaction_distance
            # Start from closer positions (better interaction)
            for offset in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                distance = min_distance + offset
                if distance < interaction_distance:  # Ensure interaction
                    x = first_plant.position.x + distance
                    y = first_plant.position.y
                    candidates.append(Position(x=int(round(x)), y=int(round(y))))

            # Also add a few slightly offset positions in y-direction (for flexibility)
            for offset in [0.2, 0.4, 0.6]:
                distance = min_distance + offset
                if distance < interaction_distance:
                    for y_offset in [-0.5, 0.5]:
                        x = first_plant.position.x + distance
                        y = first_plant.position.y + y_offset
                        candidates.append(Position(x=int(round(x)), y=int(round(y))))

        # Filter candidates
        candidates = filter_candidates(
            candidates, self.garden, self.config['geometry']['tolerance']
        )

        # Prune if too many
        max_candidates = self.config['geometry']['max_candidates']
        if len(candidates) > max_candidates:
            candidates = self._prune_candidates(candidates)

        return candidates

    def _prune_candidates(self, candidates: list[Position]) -> list[Position]:
        """Prune candidates using geometric heuristic."""
        max_candidates = self.config['geometry']['max_candidates']
        representative_variety = self.remaining_varieties[0]

        # Score each candidate
        scored_candidates = []
        for pos in candidates:
            score = geometric_heuristic(
                pos,
                self.garden,
                representative_variety,
                self.config['heuristic']['lambda_interact'],
                self.config['heuristic']['lambda_gap'],
            )
            scored_candidates.append((score, pos))

        # Sort by score (descending) and keep top K
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [pos for _, pos in scored_candidates[:max_candidates]]

    def _generate_multi_species_candidates(self, variety: PlantVariety) -> list[Position]:
        """
        Generate candidates at intersection points where plant would interact with 2+ different species.

        Strategy:
        1. Find all pairs of existing plants with different species
        2. Compute circle-circle intersections of their interaction zones with the new plant
        3. These intersection points are where the new plant can interact with both

        Args:
            variety: The variety to be placed

        Returns:
            List of candidate positions at multi-species interaction zones
        """
        candidates = []

        # Group plants by species
        species_plants = defaultdict(list)
        for plant in self.garden.plants:
            species_plants[plant.variety.species].append(plant)

        # Get species different from the new variety
        different_species = [s for s in species_plants if s != variety.species]

        if len(different_species) < 2:
            # Need at least 2 different species to create multi-species interaction
            if self.config['debug']['verbose']:
                print(
                    f'  Cannot generate multi-species candidates: only {len(different_species)} different species in garden'
                )
            return []

        # For each pair of different species, find intersection points
        max_pairs = self.config['geometry']['max_anchor_pairs']
        pair_count = 0

        for i, species1 in enumerate(different_species):
            for species2 in different_species[i + 1 :]:
                if pair_count >= max_pairs:
                    break

                # Take a few plants from each species
                plants1 = list(species_plants[species1])[:3]
                plants2 = list(species_plants[species2])[:3]

                for p1 in plants1:
                    for p2 in plants2:
                        # Calculate interaction radii with new variety
                        r1_interaction = p1.variety.radius + variety.radius
                        r2_interaction = p2.variety.radius + variety.radius

                        # Find intersection points (positions where new plant interacts with both)
                        # Use multiple factors (0.6 to 0.95) for varied interaction strengths
                        for factor in [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
                            intersections = circle_circle_intersection(
                                p1.position,
                                r1_interaction * factor,
                                p2.position,
                                r2_interaction * factor,
                            )
                            candidates.extend(intersections)

                        # Also add tangency candidates around each anchor
                        # Sample positions at interaction distance from each plant
                        for angle_idx in range(12):
                            angle = 2 * 3.14159 * angle_idx / 12
                            # Position at 0.8x interaction distance from p1
                            import math

                            x = p1.position.x + r1_interaction * 0.8 * math.cos(angle)
                            y = p1.position.y + r1_interaction * 0.8 * math.sin(angle)
                            candidates.append(Position(x=int(round(x)), y=int(round(y))))

                        pair_count += 1
                        if pair_count >= max_pairs:
                            break
                    if pair_count >= max_pairs:
                        break
            if pair_count >= max_pairs:
                break

        if self.config['debug']['verbose'] and candidates:
            print(f'  Generated {len(candidates)} multi-species interaction candidates')

        return candidates

    def _get_nutrient_balance(self) -> dict:
        """Calculate current nutrient production balance in garden."""
        totals = {Micronutrient.R: 0.0, Micronutrient.G: 0.0, Micronutrient.B: 0.0}

        for plant in self.garden.plants:
            for nutrient, val in plant.variety.nutrient_coefficients.items():
                totals[nutrient] += val

        return totals

    def _would_interact_with_two_species(self, variety: PlantVariety, position: Position) -> bool:
        """
        Check if placing a variety at position would interact with at least 2 different species.

        Args:
            variety: Variety to place
            position: Position to check

        Returns:
            True if would interact with 2+ different species, False otherwise
        """
        interacting_species = set()

        for plant in self.garden.plants:
            # Skip same species (can't exchange with same species)
            if plant.variety.species == variety.species:
                continue

            # Check if within interaction distance
            distance = calculate_distance(position, plant.position)
            interaction_distance = plant.variety.radius + variety.radius

            if distance < interaction_distance:
                interacting_species.add(plant.variety.species)

        return len(interacting_species) >= 2

    def _prioritize_varieties(self) -> list[PlantVariety]:
        """
        Prioritize varieties based on nutrient balance and interaction potential.

        Returns:
            List of varieties sorted by priority (highest priority first)
        """
        if len(self.garden.plants) == 0:
            # First plant: prioritize largest radius
            # Sort by radius (larger first), then by species for tie-breaking
            sorted_varieties = sorted(
                self.remaining_varieties, key=lambda v: (v.radius, v.species.value), reverse=True
            )
            return sorted_varieties

        # Special case: 2nd plant - prioritize larger radius
        if len(self.garden.plants) == 1:
            # Must be different species from first plant
            existing_species = {p.variety.species for p in self.garden.plants}
            available_varieties = [
                v for v in self.remaining_varieties if v.species not in existing_species
            ]

            # Sort by radius (larger first), then by species for tie-breaking
            sorted_varieties = sorted(
                available_varieties, key=lambda v: (v.radius, v.species.value), reverse=True
            )

            return sorted_varieties

        # Special case: 3rd plant - prioritize smaller radius
        if len(self.garden.plants) == 2:
            # Must be different species from existing plants
            existing_species = {p.variety.species for p in self.garden.plants}
            available_varieties = [
                v for v in self.remaining_varieties if v.species not in existing_species
            ]

            # Sort by radius (smaller first), then by species for tie-breaking
            sorted_varieties = sorted(
                available_varieties,
                key=lambda v: (v.radius, v.species.value),
                reverse=False,  # Ascending: smaller radius first
            )

            return sorted_varieties

        # Get current nutrient balance
        nutrient_totals = self._get_nutrient_balance()

        # Find most underproduced nutrient
        min_total = min(nutrient_totals.values())
        max_total = max(nutrient_totals.values())
        imbalance = max_total - min_total if max_total != min_total else 0.0

        def priority_score(variety: PlantVariety) -> float:
            """Calculate priority score for a variety."""
            score = 0.0

            # Nutrient balance contribution
            if imbalance > 0:
                for nutrient, total in nutrient_totals.items():
                    prod = variety.nutrient_coefficients.get(nutrient, 0.0)
                    if prod > 0:  # Variety produces this nutrient
                        # Higher score for producing underproduced nutrients
                        underproduction = max_total - total
                        score += prod * underproduction / (max_total + 1.0)

            # Interaction potential: prefer varieties that can interact with existing plants
            can_interact = any(p.variety.species != variety.species for p in self.garden.plants)
            if can_interact:
                score += 10.0

            # Radius preference: slightly prefer smaller radii for flexibility
            score += (4 - variety.radius) * 0.5

            return score

        sorted_varieties = sorted(self.remaining_varieties, key=priority_score, reverse=True)

        return sorted_varieties

    def _find_best_placement(self, candidates: list[Position]) -> tuple:
        """
        Find the best (variety, position) pair among all candidates and varieties.

        Returns:
            Tuple of (best_value, best_variety, best_position)
        """
        best_value = float('-inf')
        best_variety = None
        best_position = None

        # Get prioritized varieties
        prioritized_varieties = self._prioritize_varieties()

        # Group varieties by species - only evaluate one representative per species
        # This avoids redundant evaluations (e.g., 10 identical Rhododendrons)
        species_representatives = {}
        species_to_varieties = {}  # Map to get back to actual variety instances

        for variety in prioritized_varieties:
            if variety.species not in species_representatives:
                species_representatives[variety.species] = variety
                species_to_varieties[variety.species] = []
            species_to_varieties[variety.species].append(variety)

        representative_varieties = list(species_representatives.values())

        if self.config['debug']['verbose']:
            total_evaluations = len(candidates) * len(representative_varieties)
            print(
                f'  Eval: {len(candidates)} pos × {len(representative_varieties)} species = {total_evaluations} combos',
                end='',
            )

        # Evaluate each candidate position with each species representative
        eval_count = 0
        total_evaluations = len(candidates) * len(representative_varieties)
        penalized_count = 0

        for position in candidates:
            for idx, variety in enumerate(representative_varieties):
                eval_count += 1

                # Check if can place
                if not self.garden.can_place_plant(variety, position):
                    continue

                # HARD REQUIREMENT: First 3 plants MUST be different species
                if len(self.garden.plants) < 3:
                    existing_species = {p.variety.species for p in self.garden.plants}
                    if variety.species in existing_species:
                        penalized_count += 1
                        continue

                # HARD REQUIREMENT: 3rd plant onwards MUST interact with 2+ different species
                if len(self.garden.plants) >= 2 and not self._would_interact_with_two_species(variety, position):
                    penalized_count += 1
                    continue

                # Evaluate placement with simulation
                value, delta, reward = evaluate_placement(
                    self.garden,
                    variety,
                    position,
                    self.config['simulation']['T'],
                    self.config['placement']['beta'],
                    self.config['simulation']['w_short'],
                    self.config['simulation']['w_long'],
                    self.current_score,
                )

                # Add priority bonus to encourage nutrient balance
                priority_bonus = self.config['placement'].get('nutrient_bonus', 2.0)
                priority_rank = len(prioritized_varieties) - idx
                priority_weight = priority_rank / len(prioritized_varieties)

                bonus = 0.0

                # Special cases for first 3 plants: radius-based selection
                if len(self.garden.plants) == 0:
                    # 1st plant: bonus for larger radius
                    radius_bonus = variety.radius * 10.0
                    bonus += radius_bonus
                elif len(self.garden.plants) == 1:
                    # 2nd plant: bonus for larger radius (among remaining different species)
                    radius_bonus = variety.radius * 10.0
                    bonus += radius_bonus
                elif len(self.garden.plants) == 2:
                    # 3rd plant: bonus for smaller radius (among remaining different species)
                    # Negative bonus = penalty for large radius
                    radius_bonus = (4 - variety.radius) * 10.0  # Smaller radius gets higher bonus
                    bonus += radius_bonus
                elif len(self.garden.plants) > 2:
                    # Regular nutrient balance bonus for 4th plant onwards
                    totals = self._get_nutrient_balance()
                    max_total = max(totals.values())
                    min_total = min(totals.values())
                    imbalance = max_total - min_total

                    bonus += priority_bonus * priority_weight * (imbalance / (max_total + 1.0))

                value_with_bonus = value + bonus

                if value_with_bonus > best_value:
                    best_value = value_with_bonus
                    best_variety = variety
                    best_position = position

        # Map representative back to actual variety instance from remaining_varieties
        # (Pick the first available variety of that species)
        if best_variety is not None:
            for var in self.remaining_varieties:
                if var.species == best_variety.species:
                    best_variety = var
                    break

        # Print compact summary
        if self.config['debug']['verbose']:
            rejection_note = f', rejected {penalized_count}' if penalized_count > 0 else ''
            print(f'{rejection_note}')

        return best_value, best_variety, best_position
