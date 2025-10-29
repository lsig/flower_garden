"""Greedy Planting Algorithm Implementation."""

# Suppress annoying package outputs
import os  # noqa: E402

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'  # Suppress pygame welcome message
import warnings  # noqa: E402

warnings.filterwarnings('ignore')  # Suppress warnings

import copy  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from multiprocessing import Pool  # noqa: E402

from core.garden import Garden  # noqa: E402
from core.gardener import Gardener  # noqa: E402
from core.micronutrients import Micronutrient  # noqa: E402
from core.plants.plant_variety import PlantVariety  # noqa: E402
from core.point import Position  # noqa: E402
from gardeners.group10.adaptive_greedy_algorithm_1028.utils import (  # noqa: E402
    calculate_area_outside_boundary,
    calculate_distance,
    calculate_intersection_area,
    evaluate_placement,
    simulate_and_score,
)

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================
CONFIG = {
    'simulation': {
        'T': 100,  # Default turns for scoring simulation during placement
        'w_short': 0.2,  # Weight for short-term growth (turns 1-5)
        'w_long': 1.0,  # Weight for long-term growth (turns 6-T)
        'adaptive_T_min': 40,  # Minimum T for adaptive simulation (late-stage plants)
        'adaptive_T_alpha': 0.7,  # Decay shape parameter (0.7 = slower decay early, faster later)
        'area_power': 1.5,  # Power for area calculation: circle_area = π × r^area_power
    },
    'candidate_filtering': {
        'max_candidates': 50,  # Max candidates to evaluate per iteration
        'tolerance': 0.5,  # Spatial deduplication tolerance for filter_candidates
    },
    'heuristic': {
        'lambda_interact': 3.0,  # Weight for interaction density in pre-ranking
        'lambda_gap': 0.5,  # Weight for gap penalty in pre-ranking
    },
    'debug': {
        'verbose': True,  # Print debug information during placement
        'log_candidates': False,  # Log candidate generation details
    },
    'performance': {
        'parallel': True,  # Enable parallel simulation (multiprocessing)
        'num_workers': 4,  # Number of parallel workers (CPU cores)
        'parallel_threshold': 8,  # Minimum evaluations to use parallel
        'heuristic_top_k': 32,  # Number of top candidates to evaluate after cheap heuristic
        'heuristic_top_percent': 0.3,  # If top_k=0, use this percentage (0.3 = 30%)
        'finegrained_search': True,  # Enable two-stage finegrained search
        'finegrained_top_k': 4,  # Top K candidates to re-evaluate with deeper simulation
        'finegrained_T': 500,  # Deeper simulation turns for top K
    },
    'placement': {
        'epsilon': -10,  # Improvement threshold for stopping (allow small decreases)
    },
}


# Global worker function for multiprocessing
def _evaluate_placement_worker(args):
    """
    Worker function for parallel evaluation.
    Must be defined at module level for pickling.
    """
    garden, variety, position, T, beta, w_short, w_long, current_score, area_power = args
    try:
        value, delta, reward = evaluate_placement(
            garden,
            variety,
            position,
            T,
            beta,
            w_short,
            w_long,
            current_score,
            area_power=area_power,
        )
        return (value, delta, reward, variety, position)
    except Exception:
        # Return negative infinity on error
        return (float('-inf'), 0, 0, variety, position)


class GreedyGardener(Gardener):
    """Greedy planting algorithm with geometric candidate generation and nutrient balancing."""

    def __init__(
        self, garden: Garden, varieties: list[PlantVariety], simulation_turns: int | None = None
    ):
        super().__init__(garden, varieties)
        # Use global CONFIG with deep copy to avoid modification
        self.config = copy.deepcopy(CONFIG)

        # Use min(simulation_turns, config_T) if simulation_turns provided
        # This allows T in config to be a maximum, with actual turns passed at runtime
        if simulation_turns is not None:
            self.config['simulation']['T'] = min(simulation_turns, self.config['simulation']['T'])

        self.current_score = 0.0
        self.original_varieties = varieties.copy()
        self.remaining_varieties = varieties.copy()
        self.available_varieties_by_sig = self._build_variety_inventory(varieties)
        self.first_group_plants = []
        self.first_group_varieties = []
        self.first_group_signatures = []
        self.first_group_positions = []
        self.attempted_new_group_positions = []  # Track failed new group starting positions

        # Performance optimization: caching
        self.interaction_cache = {}  # Cache interaction calculations

    def _get_adaptive_T(self) -> int:
        """
        Dynamically determine simulation turns using a smooth decay function.

        Uses exponential decay: T = T_max * (T_min/T_max)^(progress^alpha)
        where progress = num_placed / total_varieties

        Early stage: longer simulations (more important placements)
        Later stage: shorter simulations (speed over accuracy)

        Parameters controlled by config:
        - T_max: simulation.T
        - T_min: simulation.adaptive_T_min
        - alpha: simulation.adaptive_T_alpha
        """

        num_placed = len(self.garden.plants)
        total_varieties = len(self.original_varieties)

        if total_varieties == 0:
            return self.config['simulation']['T']

        # Calculate placement progress (0.0 to 1.0)
        progress = num_placed / total_varieties

        # Get parameters from config
        T_max = self.config['simulation']['T']
        T_min = self.config['simulation'].get('adaptive_T_min', max(20, T_max // 5))
        alpha = self.config['simulation'].get('adaptive_T_alpha', 0.7)

        # Exponential decay with custom shaping
        # T = T_max * ((T_min/T_max) ^ (progress^alpha))
        ratio = T_min / T_max
        shaped_progress = progress**alpha

        T_dynamic = T_max * (ratio**shaped_progress)

        # Round to nearest 10 for cleaner values
        T_rounded = max(T_min, int(round(T_dynamic / 10) * 10))

        return T_rounded

    def _cheap_heuristic_score(self, variety, position) -> float:
        """
        Fast heuristic scoring without simulation.
        Used for early pruning before expensive simulation.

        Considers:
        1. Plant produce (R+G+B) weighted by nutrient demand
        2. Plant exchange potential (ideal exchange amount with neighbors)
        3. Normalized by intersection area with existing plants

        Note: Interaction bonus removed - all candidates should already have
        2-species interaction (enforced during candidate generation/filtering)
        """

        # Calculate intersection area with existing plants (using unified function)
        intersection_area = calculate_intersection_area(self.garden, variety, position)

        # Calculate area outside boundary
        area_outside = calculate_area_outside_boundary(self.garden, position, variety.radius)

        # Total effective interaction area = intersection - area_outside
        # (We want high intersection for exchange, but penalize boundary overflow)
        effective_interaction_area = max(intersection_area - area_outside * 0.5, 0.01)

        if effective_interaction_area <= 0.01:
            # No/minimal effective interaction area, very bad placement
            return 0.0

        # 1. Plant produce score (weighted by nutrient demand)
        produce_score = self._calculate_produce_score(variety)

        # 2. Exchange potential score
        exchange_score = self._calculate_exchange_potential(variety, position)

        # Total score normalized by effective interaction area
        raw_score = produce_score + exchange_score

        # Normalize by effective interaction area (reward space-efficient placements within bounds)
        normalized_score = raw_score / effective_interaction_area

        return normalized_score

    def _calculate_produce_score(self, variety) -> float:
        """
        Calculate produce score weighted by garden's nutrient demand.

        Uses ranking-based weights: lowest production gets weight 3,
        medium gets 2, highest gets 1.
        """
        from core.micronutrients import Micronutrient

        # Calculate garden's net production for each nutrient
        garden_production = {Micronutrient.R: 0.0, Micronutrient.G: 0.0, Micronutrient.B: 0.0}

        for plant in self.garden.plants:
            for nutrient, coeff in plant.variety.nutrient_coefficients.items():
                garden_production[nutrient] += coeff

        # Sort nutrients by production (lowest first)
        sorted_nutrients = sorted(garden_production.items(), key=lambda x: x[1])

        # Assign weights based on rank: lowest=3, medium=2, highest=1
        nutrient_weights = {
            sorted_nutrients[0][0]: 3.0,  # Lowest production
            sorted_nutrients[1][0]: 2.0,  # Medium production
            sorted_nutrients[2][0]: 1.0,  # Highest production
        }

        # Calculate this variety's weighted contribution
        score = 0.0
        for nutrient, coeff in variety.nutrient_coefficients.items():
            weight = nutrient_weights[nutrient]
            score += coeff * weight

        return score

    def _calculate_exchange_potential(self, variety, position) -> float:
        """
        Calculate ideal exchange potential with neighboring plants.

        Based on project rules:
        - Each plant offers 25% of its inventory of the nutrient it produces
        - Offer is split among all interaction partners
        - Exchange amount = min(offer1_per_partner, offer2_per_partner)

        Assumes steady-state inventory ≈ reservoir_capacity / 2 = 5 * radius
        """
        exchange_score = 0.0

        # Count how many plants this new plant would interact with
        interacting_plants = []
        for plant in self.garden.plants:
            # Only exchange with different species
            if plant.variety.species == variety.species:
                continue

            # Check if within interaction range (distance < r1+r2, tangent doesn't count)
            dx = position.x - plant.position.x
            dy = position.y - plant.position.y
            dist = (dx * dx + dy * dy) ** 0.5
            interaction_range = variety.radius + plant.variety.radius

            if dist < interaction_range:
                interacting_plants.append(plant)

        if not interacting_plants:
            return 0.0

        # Calculate new plant's offer per partner
        # Assume steady-state inventory = 5 * radius
        new_plant_inventory = 5.0 * variety.radius
        new_plant_total_offer = new_plant_inventory * 0.25
        new_plant_offer_per_partner = new_plant_total_offer / len(interacting_plants)

        # For each interacting plant, estimate exchange amount
        for plant in interacting_plants:
            # Count existing plant's partners (including this new one)
            existing_partners_count = 1  # At least the new plant
            for other in self.garden.plants:
                if other.variety.species != plant.variety.species:
                    dx = other.position.x - plant.position.x
                    dy = other.position.y - plant.position.y
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= (plant.variety.radius + other.variety.radius):
                        existing_partners_count += 1

            # Existing plant's offer per partner
            existing_inventory = 5.0 * plant.variety.radius
            existing_total_offer = existing_inventory * 0.25
            existing_offer_per_partner = existing_total_offer / existing_partners_count

            # Exchange amount = min of two offers
            exchange_amount = min(new_plant_offer_per_partner, existing_offer_per_partner)

            # Add to score (value each exchange)
            exchange_score += exchange_amount

        return exchange_score

    def cultivate_garden(self) -> None:
        """
        Main placement loop: iteratively place plants using greedy selection.
        """
        iteration = 0
        first_group_relaxation_used = False
        first_group_relaxation_plant_idx = None

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

            # ALWAYS use exhaustive search for better coverage
            exhaustive_candidates = self._generate_exhaustive_candidates()
            if not exhaustive_candidates:
                if self.config['debug']['verbose']:
                    print('No valid candidates found. Stopping.')
                break

            best_value, best_variety, best_position, current_used_relaxation = (
                self._find_best_placement_exhaustive_optimized(exhaustive_candidates)
            )

            # Check stopping criterion
            epsilon = self.config['placement']['epsilon']
            if best_value <= epsilon:
                if self.config['debug']['verbose']:
                    print(f'Best value {best_value:.4f} <= epsilon {epsilon}. Stopping.')
                break

            # BEFORE placing: Check relaxation conflicts
            if first_group_relaxation_used and current_used_relaxation:
                # Both previous and current use relaxation - not allowed!
                # Rollback: remove previous relaxation plant and stop first group
                if self.config['debug']['verbose']:
                    print(
                        '  [Relaxation failed: consecutive relaxation in first group. Rolling back...]'
                    )

                # Remove previous relaxation plant
                if (
                    first_group_relaxation_plant_idx is not None
                    and first_group_relaxation_plant_idx < len(self.garden.plants)
                ):
                    relaxed_plant = self.garden.plants[first_group_relaxation_plant_idx]
                    self.garden.plants.remove(relaxed_plant)
                    self.garden._used_varieties.discard(id(relaxed_plant.variety))
                    self.remaining_varieties.append(relaxed_plant.variety)
                    sig = self._variety_signature(relaxed_plant.variety)
                    if sig in self.available_varieties_by_sig:
                        self.available_varieties_by_sig[sig].append(relaxed_plant.variety)
                    # Remove from first_group tracking
                    if relaxed_plant in self.first_group_plants:
                        self.first_group_plants.remove(relaxed_plant)
                    if relaxed_plant.variety in self.first_group_varieties:
                        self.first_group_varieties.remove(relaxed_plant.variety)
                    relaxed_sig = self._variety_signature(relaxed_plant.variety)
                    if relaxed_sig in self.first_group_signatures:
                        self.first_group_signatures.remove(relaxed_sig)

                # Stop first group placement
                break

            # Place the plant
            plant = self.garden.add_plant(best_variety, best_position)

            if plant is None:
                if self.config['debug']['verbose']:
                    print(
                        f'Failed to place {best_variety.name} at ({best_position.x:.2f}, {best_position.y:.2f})'
                    )
                self._consume_variety(best_variety)
                continue

            # Update state
            self.first_group_plants.append(plant)
            self.first_group_varieties.append(best_variety)
            self.first_group_signatures.append(self._variety_signature(best_variety))
            self._consume_variety(best_variety)

            # Track relaxation for first group
            if current_used_relaxation:
                first_group_relaxation_used = True
                first_group_relaxation_plant_idx = len(self.garden.plants) - 1
                if self.config['debug']['verbose']:
                    print(f'  [Relaxation used in first group: plant #{len(self.garden.plants)}]')

            # Use adaptive T for scoring
            adaptive_T = self._get_adaptive_T()
            self.current_score = simulate_and_score(
                self.garden,
                adaptive_T,
                self.config['simulation']['w_short'],
                self.config['simulation']['w_long'],
            )

            if self.config['debug']['verbose']:
                print(
                    f'  → {best_variety.species.name[0]} at ({int(best_position.x)},{int(best_position.y)}): value={best_value:.2f}, score={self.current_score:.2f}'
                )

        # Validate and prune first group before proceeding
        if self.config['debug']['verbose']:
            print(f'\n=== First Group Complete: {len(self.garden.plants)} plants placed ===')
        self._validate_and_prune_group(start_idx=0)

        self._transplant_first_group_to_origin()
        self._cache_first_group_positions()
        self._replicate_first_group()

        # Build new groups and continue with greedy placement
        self._fill_remaining_space()

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

    def _generate_exhaustive_candidates(self) -> list[Position]:
        """
        Generate candidates by scanning the entire garden grid.
        Used as fallback when standard candidate generation fails.

        Returns positions that are:
        - Not inside existing plants (collision-free)
        - Can potentially interact with at least one existing plant
        """
        candidates = []

        # Grid sample the entire garden at integer positions
        # Use step size of 1 for comprehensive coverage
        for x in range(int(self.garden.width) + 1):
            for y in range(int(self.garden.height) + 1):
                pos = Position(x=x, y=y)

                # Check if this position is far enough from all plants (not inside any plant)
                is_valid = True
                for plant in self.garden.plants:
                    dist = (
                        (pos.x - plant.position.x) ** 2 + (pos.y - plant.position.y) ** 2
                    ) ** 0.5
                    # Must be outside the plant's core radius
                    if dist < plant.variety.radius * 0.9:
                        is_valid = False
                        break

                if is_valid:
                    candidates.append(pos)

        if self.config['debug']['verbose'] and candidates:
            print(f'  Generated {len(candidates)} exhaustive candidates')

        return candidates

    def _find_best_placement_exhaustive_optimized(self, candidates: list[Position]) -> tuple:
        """
        Optimized exhaustive search that groups candidates by interaction pattern.
        For candidates with same interaction, only evaluate the one with best space utilization.

        Returns:
            Tuple of (best_value, best_variety, best_position, used_relaxation)
        """
        best_value = float('-inf')
        best_variety = None
        best_position = None
        used_relaxation = False  # Track if we used 1-species relaxation

        # Get prioritized varieties
        prioritized_varieties = self._prioritize_varieties()

        # Evaluate all unique varieties
        signature_representatives = {}
        for variety in prioritized_varieties:
            sig = self._variety_signature(variety)
            if sig not in signature_representatives:
                signature_representatives[sig] = variety
        varieties_to_evaluate = list(signature_representatives.values())

        # From 3rd plant (index 2) onwards, require 2-species interaction
        require_two_species = len(self.garden.plants) >= 2
        garden_is_empty = len(self.garden.plants) == 0

        # Group candidates by (variety, interaction_pattern)
        from collections import defaultdict

        interaction_groups = defaultdict(list)

        for position in candidates:
            for variety in varieties_to_evaluate:
                # Check if can place
                if not self.garden.can_place_plant(variety, position):
                    continue

                # Get interacting species
                interacting_species = self._get_interacting_species(variety, position)

                # Check interaction requirements
                if garden_is_empty:
                    # First plant: no interaction required
                    pass
                elif require_two_species:
                    if len(interacting_species) < 2:
                        continue
                else:
                    if len(interacting_species) < 1:
                        continue

                # Create interaction key: (variety_sig, frozenset of interacting species)
                variety_sig = self._variety_signature(variety)
                interaction_key = (variety_sig, frozenset(interacting_species))

                # Calculate space utilization score (closer to plants = better)
                if garden_is_empty:
                    # For first plant, prefer positions closer to (0,0)
                    space_score = -((position.x**2 + position.y**2) ** 0.5)
                else:
                    min_distance = float('inf')
                    for plant in self.garden.plants:
                        dist = (
                            (position.x - plant.position.x) ** 2
                            + (position.y - plant.position.y) ** 2
                        ) ** 0.5
                        min_distance = min(min_distance, dist)
                    # Negative min_distance because we want closer positions first
                    space_score = -min_distance

                # Store: (position, variety, space_score)
                interaction_groups[interaction_key].append((position, variety, space_score))

        if self.config['debug']['verbose']:
            total_combos = sum(len(group) for group in interaction_groups.values())
            print(
                f'  Exhaustive eval: {len(candidates)} pos × {len(varieties_to_evaluate)} varieties = {total_combos} combos in {len(interaction_groups)} groups'
            )

        # STRATEGY C OPTIMIZATION: Early Pruning with Cheap Heuristics
        # Step 1: Collect representatives from each interaction group
        representatives = []
        for _interaction_key, group in interaction_groups.items():
            # Sort by space_score (higher = better = closer to existing plants)
            group.sort(key=lambda x: x[2], reverse=True)
            # Take the best one from each group
            position, variety, space_score = group[0]
            representatives.append((position, variety, space_score))

        # Step 2: Apply cheap heuristic scoring
        candidates_with_heuristic = []
        for position, variety, space_score in representatives:
            cheap_score = self._cheap_heuristic_score(variety, position)
            candidates_with_heuristic.append((cheap_score, position, variety, space_score))

        # Step 3: Sort by cheap score and take top K candidates
        candidates_with_heuristic.sort(reverse=True, key=lambda x: x[0])

        # Use heuristic_top_k if set, otherwise use percentage
        heuristic_top_k = self.config.get('performance', {}).get('heuristic_top_k', 10)
        if heuristic_top_k > 0:
            num_to_evaluate = min(heuristic_top_k, len(candidates_with_heuristic))
        else:
            heuristic_top_percent = self.config.get('performance', {}).get(
                'heuristic_top_percent', 0.3
            )
            num_to_evaluate = max(10, int(len(candidates_with_heuristic) * heuristic_top_percent))

        top_candidates = candidates_with_heuristic[:num_to_evaluate]

        # Step 4: Run expensive simulation on top candidates
        # Use adaptive T based on number of plants
        adaptive_T = self._get_adaptive_T()

        evaluations_run = len(top_candidates)

        # Decide whether to use parallel or serial evaluation
        use_parallel = self.config.get('performance', {}).get(
            'parallel', False
        ) and evaluations_run >= self.config.get('performance', {}).get('parallel_threshold', 8)

        # Stage 1: Initial evaluation with adaptive T
        first_stage_results = []

        if use_parallel:
            # Parallel evaluation using multiprocessing
            try:
                # Get area_power from config
                area_power = self.config['simulation'].get('area_power', 2.0)

                # Prepare arguments for parallel execution
                eval_args = [
                    (
                        copy.deepcopy(self.garden),  # Deep copy garden for each worker
                        variety,
                        position,
                        adaptive_T,
                        0.0,  # beta unused (kept for compatibility)
                        self.config['simulation']['w_short'],
                        self.config['simulation']['w_long'],
                        self.current_score,
                        area_power,
                    )
                    for _cheap_score, position, variety, _space_score in top_candidates
                ]

                # Run parallel evaluation
                num_workers = self.config.get('performance', {}).get('num_workers', 4)
                with Pool(processes=num_workers) as pool:
                    results = pool.map(_evaluate_placement_worker, eval_args)

                # Collect all results
                for value, _delta, _reward, variety, position in results:
                    first_stage_results.append((value, variety, position))
                    if value > best_value:
                        best_value = value
                        best_variety = variety
                        best_position = position

            except Exception as e:
                # Fall back to serial if parallel fails
                if self.config['debug']['verbose']:
                    print(f'    Parallel evaluation failed, falling back to serial: {e}')
                use_parallel = False

        if not use_parallel:
            # Serial evaluation (original method)
            area_power = self.config['simulation'].get('area_power', 2.0)

            for _cheap_score, position, variety, _space_score in top_candidates:
                # Evaluate placement with simulation using adaptive T
                value, delta, reward = evaluate_placement(
                    self.garden,
                    variety,
                    position,
                    adaptive_T,
                    0.0,  # beta unused (kept for compatibility)
                    self.config['simulation']['w_short'],
                    self.config['simulation']['w_long'],
                    self.current_score,
                    area_power=area_power,
                )

                first_stage_results.append((value, variety, position))
                if value > best_value:
                    best_value = value
                    best_variety = variety
                    best_position = position

        # Stage 2: Finegrained search - re-evaluate top K with deeper simulation
        finegrained_enabled = self.config.get('performance', {}).get('finegrained_search', False)
        if finegrained_enabled and len(first_stage_results) > 1:
            finegrained_top_k = self.config.get('performance', {}).get('finegrained_top_k', 5)
            finegrained_T = self.config.get('performance', {}).get('finegrained_T', 200)

            # Sort by value and take top K
            first_stage_results.sort(reverse=True, key=lambda x: x[0])
            top_k_for_refinement = first_stage_results[
                : min(finegrained_top_k, len(first_stage_results))
            ]

            if self.config['debug']['verbose']:
                print(
                    f'    Finegrained: re-evaluating top {len(top_k_for_refinement)} with T={finegrained_T}'
                )

            # Re-evaluate with deeper simulation
            best_value = float('-inf')
            best_variety = None
            best_position = None

            use_parallel_fg = (
                self.config.get('performance', {}).get('parallel', False)
                and len(top_k_for_refinement) >= 4  # Use parallel if >= 4 candidates
            )

            if use_parallel_fg:
                try:
                    # Get area_power from config
                    area_power = self.config['simulation'].get('area_power', 2.0)

                    eval_args_fg = [
                        (
                            copy.deepcopy(self.garden),
                            variety,
                            position,
                            finegrained_T,
                            0.0,  # beta unused (kept for compatibility)
                            self.config['simulation']['w_short'],
                            self.config['simulation']['w_long'],
                            self.current_score,
                            area_power,
                        )
                        for value, variety, position in top_k_for_refinement
                    ]

                    with Pool(processes=num_workers) as pool:
                        results_fg = pool.map(_evaluate_placement_worker, eval_args_fg)

                    for value, _delta, _reward, variety, position in results_fg:
                        if value > best_value:
                            best_value = value
                            best_variety = variety
                            best_position = position

                except Exception:
                    use_parallel_fg = False

            if not use_parallel_fg:
                area_power = self.config['simulation'].get('area_power', 2.0)

                for _old_value, variety, position in top_k_for_refinement:
                    value, delta, reward = evaluate_placement(
                        self.garden,
                        variety,
                        position,
                        finegrained_T,
                        0.0,  # beta unused (kept for compatibility)
                        self.config['simulation']['w_short'],
                        self.config['simulation']['w_long'],
                        self.current_score,
                        area_power=area_power,
                    )

                    if value > best_value:
                        best_value = value
                        best_variety = variety
                        best_position = position

        if self.config['debug']['verbose']:
            skipped_pattern = sum(
                len(group) - 1 for group in interaction_groups.values() if len(group) > 1
            )
            skipped_pruning = len(representatives) - evaluations_run
            print(
                f'    Ran {evaluations_run} simulations (T={adaptive_T}), skipped {skipped_pattern} (pattern) + {skipped_pruning} (pruning)'
            )

        # PHASE 2: If nothing found with strict requirement, try relaxed
        if best_variety is None and require_two_species:
            if self.config['debug']['verbose']:
                print('    No 2-species found. Trying 1-species relaxation...')

            used_relaxation = True  # Mark that we're using relaxation

            # Re-group with relaxed constraint
            interaction_groups_relaxed = defaultdict(list)

            for position in candidates:
                for variety in varieties_to_evaluate:
                    if not self.garden.can_place_plant(variety, position):
                        continue

                    interacting_species = self._get_interacting_species(variety, position)

                    # Relaxed: just need 1+ species
                    if len(interacting_species) < 1:
                        continue

                    variety_sig = self._variety_signature(variety)
                    interaction_key = (variety_sig, frozenset(interacting_species))

                    min_distance = float('inf')
                    for plant in self.garden.plants:
                        dist = (
                            (position.x - plant.position.x) ** 2
                            + (position.y - plant.position.y) ** 2
                        ) ** 0.5
                        min_distance = min(min_distance, dist)

                    space_score = -min_distance
                    interaction_groups_relaxed[interaction_key].append(
                        (position, variety, space_score)
                    )

            # Apply early pruning for relaxed candidates too
            representatives_relaxed = []
            for _interaction_key, group in interaction_groups_relaxed.items():
                group.sort(key=lambda x: x[2], reverse=True)
                position, variety, space_score = group[0]
                cheap_score = self._cheap_heuristic_score(variety, position)
                representatives_relaxed.append((cheap_score, position, variety))

            # Sort and take top 30%
            representatives_relaxed.sort(reverse=True, key=lambda x: x[0])
            num_to_evaluate_relaxed = max(10, int(len(representatives_relaxed) * 0.3))
            top_relaxed = representatives_relaxed[:num_to_evaluate_relaxed]

            # Use parallel evaluation for relaxed candidates too
            use_parallel_relaxed = self.config.get('performance', {}).get(
                'parallel', False
            ) and len(top_relaxed) >= self.config.get('performance', {}).get(
                'parallel_threshold', 8
            )

            if use_parallel_relaxed:
                try:
                    # Get area_power from config
                    area_power = self.config['simulation'].get('area_power', 2.0)

                    eval_args_relaxed = [
                        (
                            copy.deepcopy(self.garden),
                            variety,
                            position,
                            adaptive_T,
                            0.0,  # beta unused (kept for compatibility)
                            self.config['simulation']['w_short'],
                            self.config['simulation']['w_long'],
                            self.current_score,
                            area_power,
                        )
                        for cheap_score, position, variety in top_relaxed
                    ]

                    num_workers = self.config.get('performance', {}).get('num_workers', 4)
                    with Pool(processes=num_workers) as pool:
                        results_relaxed = pool.map(_evaluate_placement_worker, eval_args_relaxed)

                    for value, _delta, _reward, variety, position in results_relaxed:
                        if value > best_value:
                            best_value = value
                            best_variety = variety
                            best_position = position

                except Exception:
                    use_parallel_relaxed = False

            if not use_parallel_relaxed:
                area_power = self.config['simulation'].get('area_power', 2.0)

                for _cheap_score, position, variety in top_relaxed:
                    value, delta, reward = evaluate_placement(
                        self.garden,
                        variety,
                        position,
                        adaptive_T,
                        0.0,  # beta unused (kept for compatibility)
                        self.config['simulation']['w_short'],
                        self.config['simulation']['w_long'],
                        self.current_score,
                        area_power=area_power,
                    )

                    if value > best_value:
                        best_value = value
                        best_variety = variety
                        best_position = position

        # Map representative back to actual variety instance
        if best_variety is not None:
            best_sig = self._variety_signature(best_variety)
            for var in self.remaining_varieties:
                if self._variety_signature(var) == best_sig:
                    best_variety = var
                    break

        return best_value, best_variety, best_position, used_relaxation

    def _get_interacting_species(self, variety: PlantVariety, position: Position) -> set:
        """
        Get the set of species this variety would interact with at this position.
        Uses caching to avoid redundant calculations.
        """
        # Cache key: (variety_sig, position, garden_size)
        # Garden size changes when we place plants, so cache auto-invalidates
        cache_key = (
            self._variety_signature(variety),
            (int(position.x * 10), int(position.y * 10)),  # Round to 0.1 precision
            len(self.garden.plants),
        )

        if cache_key in self.interaction_cache:
            return self.interaction_cache[cache_key]

        # Calculate interactions
        interacting_species = set()
        for plant in self.garden.plants:
            if plant.variety.species == variety.species:
                continue

            distance = calculate_distance(position, plant.position)
            interaction_distance = plant.variety.radius + variety.radius

            if distance < interaction_distance:
                interacting_species.add(plant.variety.species)

        # Store in cache
        self.interaction_cache[cache_key] = interacting_species
        return interacting_species

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

    def _would_interact_with_any_species(self, variety: PlantVariety, position: Position) -> bool:
        """
        Check if placing a variety at position would interact with at least 1 different species.

        Args:
            variety: Variety to place
            position: Position to check

        Returns:
            True if would interact with 1+ different species, False otherwise
        """
        for plant in self.garden.plants:
            # Skip same species
            if plant.variety.species == variety.species:
                continue

            # Check if within interaction distance
            distance = calculate_distance(position, plant.position)
            interaction_distance = plant.variety.radius + variety.radius

            if distance < interaction_distance:
                return True

        return False

    def _plant_interacts_with_two_species(self, plant) -> bool:
        """
        Check if a placed plant currently interacts with at least 2 different species.

        Args:
            plant: Plant to check

        Returns:
            True if interacts with 2+ different species, False otherwise
        """
        interacting_species = set()

        for other_plant in self.garden.plants:
            if other_plant == plant:
                continue

            # Skip same species
            if other_plant.variety.species == plant.variety.species:
                continue

            # Check if within interaction distance
            distance = calculate_distance(plant.position, other_plant.position)
            interaction_distance = plant.variety.radius + other_plant.variety.radius

            if distance < interaction_distance:
                interacting_species.add(other_plant.variety.species)

        return len(interacting_species) >= 2

    def _validate_and_prune_group(self, start_idx: int = 0) -> int:
        """
        Validate all plants in the current group (from start_idx onwards)
        and iteratively remove those that don't interact with 2 species.

        This is called after group construction to ensure quality.
        Removal is iterative: if removing a plant causes neighbors to lose
        2-species interaction, those neighbors are also removed.

        Args:
            start_idx: Index in garden.plants to start validation from (default 0 for full garden)

        Returns:
            Number of plants removed
        """
        if len(self.garden.plants) <= start_idx:
            return 0

        removed_count = 0
        changed = True

        if self.config['debug']['verbose']:
            print(f'\n=== Validating Group (plants {start_idx}-{len(self.garden.plants) - 1}) ===')

        while changed:
            changed = False

            # Check plants from end to start (to avoid index shifting issues)
            for i in range(len(self.garden.plants) - 1, start_idx - 1, -1):
                if i >= len(self.garden.plants):
                    continue

                plant = self.garden.plants[i]

                # First 2 plants (indices 0-1) don't need 2-species requirement
                # From 3rd plant (index 2) onwards, require 2-species interaction
                if i < 2:
                    continue

                # Check if plant has 2-species interaction
                if not self._plant_interacts_with_two_species(plant):
                    if self.config['debug']['verbose']:
                        species_name = plant.variety.species.name[0]
                        print(
                            f'  Removing plant #{i} ({species_name}) - lacks 2-species interaction'
                        )

                    # Remove plant from garden
                    self.garden.plants.remove(plant)
                    self.garden._used_varieties.discard(id(plant.variety))

                    # Return variety to available pool
                    self.remaining_varieties.append(plant.variety)
                    sig = self._variety_signature(plant.variety)
                    if sig in self.available_varieties_by_sig:
                        self.available_varieties_by_sig[sig].append(plant.variety)

                    # Remove from first_group tracking if applicable
                    if plant in self.first_group_plants:
                        self.first_group_plants.remove(plant)
                    if plant.variety in self.first_group_varieties:
                        self.first_group_varieties.remove(plant.variety)
                    variety_sig = self._variety_signature(plant.variety)
                    if variety_sig in self.first_group_signatures:
                        self.first_group_signatures.remove(variety_sig)

                    removed_count += 1
                    changed = True
                    break  # Restart validation after removal

        if self.config['debug']['verbose'] and removed_count > 0:
            print(f'  Total removed: {removed_count} plants')
            print(f'  Remaining in group: {len(self.garden.plants) - start_idx} plants')

        return removed_count

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

    def _build_variety_inventory(self, varieties: list[PlantVariety]) -> dict:
        inventory = defaultdict(list)
        for variety in varieties:
            inventory[self._variety_signature(variety)].append(variety)
        return inventory

    def _variety_signature(self, variety: PlantVariety) -> tuple:
        nutrient_tuple = tuple(
            sorted(
                (nutrient.name, value) for nutrient, value in variety.nutrient_coefficients.items()
            )
        )
        return (variety.name, variety.radius, variety.species, nutrient_tuple)

    def _consume_variety(self, variety: PlantVariety) -> None:
        if variety in self.remaining_varieties:
            self.remaining_varieties.remove(variety)
        signature = self._variety_signature(variety)
        pool = self.available_varieties_by_sig.get(signature)
        if pool and variety in pool:
            pool.remove(variety)

    def _remove_from_remaining(self, variety: PlantVariety) -> None:
        if variety in self.remaining_varieties:
            self.remaining_varieties.remove(variety)

    def _return_varieties(self, varieties: list[PlantVariety]) -> None:
        for variety in varieties:
            signature = self._variety_signature(variety)
            self.available_varieties_by_sig[signature].append(variety)
            if variety not in self.remaining_varieties:
                self.remaining_varieties.append(variety)

    def _transplant_first_group_to_origin(self) -> None:
        if not self.first_group_plants:
            return

        min_x = min(plant.position.x for plant in self.first_group_plants)
        min_y = min(plant.position.y for plant in self.first_group_plants)

        if min_x == 0 and min_y == 0:
            return

        for plant in self.first_group_plants:
            plant.position.x -= min_x
            plant.position.y -= min_y

    def _cache_first_group_positions(self) -> None:
        if not self.first_group_plants:
            self.first_group_positions = []
            return

        self.first_group_positions = [
            Position(x=plant.position.x, y=plant.position.y) for plant in self.first_group_plants
        ]

    def _has_group_supply(self) -> bool:
        if not self.first_group_signatures:
            return False

        required = Counter(self.first_group_signatures)
        for signature, amount in required.items():
            available = len(self.available_varieties_by_sig.get(signature, []))
            if available < amount:
                return False
        return True

    def _allocate_varieties_for_group(self) -> list[PlantVariety] | None:
        allocated = []
        temp_tracking = defaultdict(list)

        for signature in self.first_group_signatures:
            pool = self.available_varieties_by_sig.get(signature)
            if not pool:
                for sig, items in temp_tracking.items():
                    self.available_varieties_by_sig[sig].extend(items)
                return None
            variety = pool.pop()
            allocated.append(variety)
            temp_tracking[signature].append(variety)

        for variety in allocated:
            self._remove_from_remaining(variety)

        return allocated

    def _group_within_bounds(self, positions: list[Position], offset_x: int, offset_y: int) -> bool:
        for pos in positions:
            new_x = pos.x + offset_x
            new_y = pos.y + offset_y
            if new_x < 0 or new_x > self.garden.width:
                return False
            if new_y < 0 or new_y > self.garden.height:
                return False
        return True

    def _can_place_group_at(self, positions: list[Position], offset_x: int, offset_y: int) -> bool:
        new_positions = []

        for variety, rel_pos in zip(self.first_group_varieties, positions, strict=False):
            target = Position(x=rel_pos.x + offset_x, y=rel_pos.y + offset_y)

            for existing in self.garden.plants:
                distance = calculate_distance(target, existing.position)
                min_distance = max(variety.radius, existing.variety.radius)
                if distance < min_distance:
                    return False

            for placed_pos, placed_variety in new_positions:
                distance = calculate_distance(target, placed_pos)
                min_distance = max(variety.radius, placed_variety.radius)
                if distance < min_distance:
                    return False

            new_positions.append((target, variety))

        return True

    def _place_group_at(
        self, varieties: list[PlantVariety], positions: list[Position], offset_x: int, offset_y: int
    ) -> bool:
        new_plants = []

        for variety, rel_pos in zip(varieties, positions, strict=False):
            absolute_pos = Position(x=rel_pos.x + offset_x, y=rel_pos.y + offset_y)
            plant = self.garden.add_plant(variety, absolute_pos)
            if plant is None:
                for created in new_plants:
                    if created in self.garden.plants:
                        self.garden.plants.remove(created)
                        self.garden._used_varieties.discard(id(created.variety))
                return False
            new_plants.append(plant)

        return True

    def _replicate_first_group(self) -> None:
        if not self.first_group_positions or not self.first_group_varieties:
            return

        placed_any = False
        clones_placed = 0

        while self._has_group_supply():
            found_spot = False

            for offset_y in range(int(self.garden.height) + 1):
                for offset_x in range(int(self.garden.width) + 1):
                    if offset_x == 0 and offset_y == 0:
                        continue

                    if not self._group_within_bounds(
                        self.first_group_positions, offset_x, offset_y
                    ):
                        continue

                    if not self._can_place_group_at(self.first_group_positions, offset_x, offset_y):
                        continue

                    varieties = self._allocate_varieties_for_group()
                    if not varieties:
                        return

                    if not self._place_group_at(
                        varieties, self.first_group_positions, offset_x, offset_y
                    ):
                        self._return_varieties(varieties)
                        continue

                    placed_any = True
                    clones_placed += 1
                    if self.config['debug']['verbose']:
                        print(f'  → clone #{clones_placed} offset=({offset_x},{offset_y})')
                    found_spot = True
                    break

                if found_spot:
                    break

            if not found_spot:
                break

        if placed_any:
            adaptive_T = self._get_adaptive_T()
            self.current_score = simulate_and_score(
                self.garden,
                adaptive_T,
                self.config['simulation']['w_short'],
                self.config['simulation']['w_long'],
            )
            if self.config['debug']['verbose']:
                print(f'Replicated first group {clones_placed} times')

    def _fill_remaining_space(self) -> None:
        """
        Try to build new independent groups, then continue with greedy one-by-one placement.
        New groups are built with internal 2-species interaction only.
        After new groups, remaining plants use greedy placement with global 2-species interaction.
        """
        round_num = 1

        # Try to build new groups
        while self.remaining_varieties and len(self.remaining_varieties) >= 3:
            if self.config['debug']['verbose']:
                print(f'\n=== Round {round_num}: Building New Group ===')
                print(f'{len(self.remaining_varieties)} varieties remaining')

            # Try to build a new group
            initial_plant_count = len(self.garden.plants)
            new_group_built = self._build_new_independent_group()

            if not new_group_built:
                if self.config['debug']['verbose']:
                    print('Could not build new group. Switching to greedy placement.')
                break

            new_group_size = len(self.garden.plants) - initial_plant_count
            if self.config['debug']['verbose']:
                print(f'New group successfully built: {new_group_size} plants')

            # Validate and prune the newly built group
            removed = self._validate_and_prune_group(start_idx=initial_plant_count)
            if removed > 0:
                new_group_size -= removed
                if self.config['debug']['verbose']:
                    print(f'After validation: {new_group_size} plants remain in group')

            round_num += 1

        # Continue with greedy one-by-one placement for remaining varieties
        if self.remaining_varieties:
            if self.config['debug']['verbose']:
                print('\n=== Continuing Greedy Placement ===')
                print(f'{len(self.remaining_varieties)} varieties remaining')

            iteration = 0
            relaxation_used = False
            relaxation_plant_idx = None

            while self.remaining_varieties:
                iteration += 1

                # ALWAYS use exhaustive search for better coverage
                exhaustive_candidates = self._generate_exhaustive_candidates()
                if not exhaustive_candidates:
                    if self.config['debug']['verbose']:
                        print('No valid candidates found. Stopping.')
                    break

                best_value, best_variety, best_position, current_used_relaxation = (
                    self._find_best_placement_exhaustive_optimized(exhaustive_candidates)
                )

                # Check if no valid placement found
                if best_variety is None or best_position is None:
                    if self.config['debug']['verbose']:
                        print('No valid placement found. Stopping.')
                    break

                # Check stopping criterion
                epsilon = self.config['placement']['epsilon']
                if best_value <= epsilon:
                    if self.config['debug']['verbose']:
                        print(f'Best value {best_value:.4f} <= epsilon {epsilon}. Stopping.')
                    break

                # BEFORE placing: Check if previous plant used relaxation AND current also uses relaxation
                if relaxation_used and current_used_relaxation:
                    # Both previous and current use relaxation - not allowed!
                    # Rollback: remove previous relaxation plant and stop
                    if self.config['debug']['verbose']:
                        print(
                            '  [Relaxation failed: consecutive relaxation detected. Rolling back...]'
                        )

                    # Remove previous relaxation plant
                    if relaxation_plant_idx is not None and relaxation_plant_idx < len(
                        self.garden.plants
                    ):
                        relaxed_plant = self.garden.plants[relaxation_plant_idx]
                        self.garden.plants.remove(relaxed_plant)
                        self.garden._used_varieties.discard(id(relaxed_plant.variety))
                        self.remaining_varieties.append(relaxed_plant.variety)
                        sig = self._variety_signature(relaxed_plant.variety)
                        if sig in self.available_varieties_by_sig:
                            self.available_varieties_by_sig[sig].append(relaxed_plant.variety)

                    # Stop greedy placement
                    break

                # Place the plant
                plant = self.garden.add_plant(best_variety, best_position)

                if plant is None:
                    self._consume_variety(best_variety)
                    continue

                self._consume_variety(best_variety)

                # AFTER placing: Check if previous relaxation was successful
                if (
                    relaxation_used
                    and not current_used_relaxation
                    and self._plant_interacts_with_two_species(plant)
                    and relaxation_plant_idx is not None
                    and relaxation_plant_idx < len(self.garden.plants)
                ):
                    # Previous plant used relaxation, current plant doesn't
                    # Check if current plant has 2-species interaction
                    relaxed_plant = self.garden.plants[relaxation_plant_idx]
                    if self._plant_interacts_with_two_species(relaxed_plant):
                        # Perfect! Relaxation succeeded, reset flag
                        relaxation_used = False
                        relaxation_plant_idx = None
                        if self.config['debug']['verbose']:
                            print('  [Relaxation successful: restored 2-species interaction]')

                # Set relaxation flag for current plant
                if current_used_relaxation:
                    # This plant used relaxation during search
                    relaxation_used = True
                    relaxation_plant_idx = len(self.garden.plants) - 1
                    if self.config['debug']['verbose']:
                        print(
                            f'  [Relaxation used: 1-species interaction at plant #{len(self.garden.plants)}]'
                        )

                # Update score with adaptive T
                adaptive_T = self._get_adaptive_T()
                self.current_score = simulate_and_score(
                    self.garden,
                    adaptive_T,
                    self.config['simulation']['w_short'],
                    self.config['simulation']['w_long'],
                )

                if self.config['debug']['verbose']:
                    print(
                        f'  → {best_variety.species.name[0]} at ({int(best_position.x)},{int(best_position.y)}): value={best_value:.2f}, score={self.current_score:.2f}'
                    )

            # After loop ends, check if last plant used relaxation
            # If so, remove it (can't have relaxation as final plant)
            if relaxation_used and relaxation_plant_idx is not None:
                if self.config['debug']['verbose']:
                    print(
                        '  [Removing final relaxation plant: cannot end with 1-species interaction]'
                    )

                if relaxation_plant_idx < len(self.garden.plants):
                    relaxed_plant = self.garden.plants[relaxation_plant_idx]
                    self.garden.plants.remove(relaxed_plant)
                    self.garden._used_varieties.discard(id(relaxed_plant.variety))
                    self.remaining_varieties.append(relaxed_plant.variety)
                    sig = self._variety_signature(relaxed_plant.variety)
                    if sig in self.available_varieties_by_sig:
                        self.available_varieties_by_sig[sig].append(relaxed_plant.variety)

        if self.config['debug']['verbose'] and self.remaining_varieties:
            print(f'\n{len(self.remaining_varieties)} varieties left')

        # Final validation: ensure all plants in garden have 2-species interaction
        # This catches any plants that may have lost interactions during the process
        if len(self.garden.plants) > 3:
            if self.config['debug']['verbose']:
                print('\n=== Final Garden Validation ===')
            self._validate_and_prune_group(start_idx=0)

    def _build_new_independent_group(self) -> bool:
        """
        Try to build a new group of at least 3 plants.
        Try multiple starting positions until successful.
        Returns True if successful, False otherwise.
        """
        # Try multiple starting positions
        max_position_attempts = 20  # Try up to 20 different starting positions

        for position_attempt in range(max_position_attempts):
            if self.config['debug']['verbose'] and position_attempt > 0:
                print(f'  Trying starting position #{position_attempt + 1}...')

            new_group_start_idx = len(self.garden.plants)
            new_group_plants = []
            first_plant_position = None
            relaxation_used = False  # Track if we've used the 1-species relaxation
            relaxation_plant_idx = None  # Index of plant that used relaxation
            relaxation_used_at_size = None  # Track group size when relaxation was used

            # Try to place at least 3 plants for this new group
            for plant_num in range(1, 100):  # Max 100 attempts per position
                new_group_size = len(self.garden.plants) - new_group_start_idx

                if self.config['debug']['verbose']:
                    print(
                        f'  Iter {plant_num}: {new_group_size} in group, {len(self.remaining_varieties)} remain'
                    )

                # Generate candidates for this plant of the new group
                if new_group_size == 0:
                    # First plant: find next available position (skip attempted ones)
                    candidates = self._find_next_positions_for_new_group()
                else:
                    # 2nd+ plant: ALWAYS use exhaustive search for comprehensive coverage
                    candidates = self._generate_exhaustive_candidates()

                if not candidates:
                    break

                # Find best placement for new group
                if new_group_size < 3:
                    # For first 3 plants: use special logic with forced placement
                    best_value, best_variety, best_position, used_relaxation = (
                        self._find_best_placement_for_new_group(
                            candidates, new_group_start_idx, relaxation_used
                        )
                    )
                else:
                    # For 4+ plants: use standard exhaustive optimized search
                    best_value, best_variety, best_position, used_relaxation = (
                        self._find_best_placement_exhaustive_optimized(candidates)
                    )

                if best_variety is None or best_position is None:
                    if self.config['debug']['verbose'] and new_group_size < 3:
                        print(f'  No valid placement found for plant #{new_group_size + 1}')
                    break

                # Place the plant
                plant = self.garden.add_plant(best_variety, best_position)

                if plant is None:
                    self._consume_variety(best_variety)
                    continue

                new_group_plants.append(plant)
                self._consume_variety(best_variety)

                # Record if this plant used relaxation
                # For first 3 plants: check the returned flag
                # For 4+ plants: check if plant actually has 2-species interaction
                if new_group_size < 3:
                    if used_relaxation and not relaxation_used:
                        # First time using relaxation in this group
                        relaxation_used = True
                        relaxation_plant_idx = len(self.garden.plants) - 1
                        relaxation_used_at_size = (
                            new_group_size + 1
                        )  # Size after placing this plant
                        if self.config['debug']['verbose']:
                            print(
                                f'  [Relaxation used: 1-species interaction allowed at plant #{relaxation_used_at_size}]'
                            )
                else:
                    # For 4+ plants: check if plant has 2-species interaction
                    if not relaxation_used and not self._plant_interacts_with_two_species(plant):
                        relaxation_used = True
                        relaxation_plant_idx = len(self.garden.plants) - 1
                        relaxation_used_at_size = new_group_size + 1
                        if self.config['debug']['verbose']:
                            print(
                                f'  [Relaxation used: 1-species interaction allowed at plant #{relaxation_used_at_size}]'
                            )

                # Check if previously relaxed plant now connects to 2+ species
                # If so, reset relaxation
                if relaxation_plant_idx is not None and relaxation_plant_idx < len(
                    self.garden.plants
                ):
                    relaxed_plant = self.garden.plants[relaxation_plant_idx]
                    if self._plant_interacts_with_two_species(relaxed_plant):
                        relaxation_used = False
                        relaxation_plant_idx = None
                        relaxation_used_at_size = None
                        if self.config['debug']['verbose']:
                            print(
                                '  [Relaxation refreshed: previous 1-species plant now connects to 2+ species]'
                            )

                # Record first plant position
                if new_group_size == 0:
                    first_plant_position = best_position

                if self.config['debug']['verbose']:
                    species_letter = best_variety.species.name[0]
                    print(
                        f'  → {species_letter} at ({int(best_position.x)},{int(best_position.y)})'
                    )

            # Check if we built a valid group
            final_size = len(self.garden.plants) - new_group_start_idx

            # Determine if this group is acceptable
            is_acceptable = False
            if final_size >= 3:
                # If relaxation was used, check if next plant has 2-species interaction
                if relaxation_used_at_size is not None:
                    plants_after_relaxation = final_size - relaxation_used_at_size
                    if plants_after_relaxation >= 1:
                        # Check if the plant AFTER relaxation has 2-species interaction
                        plant_after_idx = new_group_start_idx + relaxation_used_at_size
                        if plant_after_idx < len(self.garden.plants):
                            plant_after = self.garden.plants[plant_after_idx]
                            if self._plant_interacts_with_two_species(plant_after):
                                # Good: relaxation was used and next plant has 2-species
                                is_acceptable = True
                                if self.config['debug']['verbose']:
                                    print(
                                        f'  Group accepted: {final_size} plants, relaxation at #{relaxation_used_at_size} restored by next plant'
                                    )
                            else:
                                # Bad: relaxation was used but next plant also doesn't have 2-species
                                if self.config['debug']['verbose']:
                                    print(
                                        f'  Group rejected: {final_size} plants, relaxation not restored (next plant lacks 2-species)'
                                    )
                                is_acceptable = False
                        else:
                            # No plant after relaxation
                            if self.config['debug']['verbose']:
                                print(
                                    f'  Group rejected: {final_size} plants but stopped immediately after relaxation'
                                )
                            is_acceptable = False
                    else:
                        # Bad: relaxation was used and no more plants could be added
                        if self.config['debug']['verbose']:
                            print(
                                f'  Group rejected: {final_size} plants but stopped immediately after relaxation'
                            )
                        is_acceptable = False
                else:
                    # No relaxation used, group is good if >= 3 plants
                    is_acceptable = True

            if is_acceptable:
                # Success!
                if self.config['debug']['verbose']:
                    print(f'  Successfully built new group with {final_size} plants!')
                return True
            else:
                # Failed with this starting position
                # Record the attempted position
                if first_plant_position is not None:
                    self.attempted_new_group_positions.append(
                        (int(first_plant_position.x), int(first_plant_position.y))
                    )

                # Remove incomplete group
                for i in range(len(self.garden.plants) - 1, new_group_start_idx - 1, -1):
                    plant = self.garden.plants[i]
                    self.garden.plants.remove(plant)
                    self.garden._used_varieties.discard(id(plant.variety))
                    # Return variety to available pool
                    if plant.variety not in self.remaining_varieties:
                        self.remaining_varieties.append(plant.variety)
                        sig = self._variety_signature(plant.variety)
                        if sig in self.available_varieties_by_sig:
                            self.available_varieties_by_sig[sig].append(plant.variety)

                # Continue to next starting position
                continue

        # Failed to build a group with any starting position
        return False

    def _find_next_positions_for_new_group(self) -> list[Position]:
        """
        Find next available position for new group's first plant.
        Skip positions that have already been attempted and failed.
        """
        if not self.remaining_varieties:
            return []

        prioritized = self._prioritize_varieties()
        if not prioritized:
            return []

        first_variety = prioritized[0]

        # Scan from left to right, top to bottom
        for x in range(int(self.garden.width) + 1):
            for y in range(int(self.garden.height) + 1):
                # Skip positions that have been attempted and failed
                if (x, y) in self.attempted_new_group_positions:
                    continue

                position = Position(x=x, y=y)
                if self.garden.can_place_plant(first_variety, position):
                    if self.config['debug']['verbose']:
                        print(f'  New group starting at: ({x}, {y})')
                    return [position]

        return []

    def _find_best_placement_for_new_group(
        self, candidates: list[Position], new_group_start_idx: int, relaxation_used: bool = False
    ) -> tuple:
        """
        Find best placement for new group plants.
        New group plants can interact with entire garden (including old groups).
        Only requirement: first 3 plants of new group must be different species.

        For 4th+ plant: if no 2-species interaction found and relaxation not used,
        allow 1-species interaction as fallback.

        Returns: (best_value, best_variety, best_position, used_relaxation)
        """
        best_value = float('-inf')
        best_variety = None
        best_position = None
        used_relaxation = False

        new_group_size = len(self.garden.plants) - new_group_start_idx
        prioritized_varieties = self._prioritize_varieties()

        # For first 3 plants of new group: manually filter by species
        # For 4+ plants: evaluate all unique varieties
        if new_group_size < 3:
            # Get species already in new group
            existing_species_in_new_group = {
                self.garden.plants[i].variety.species
                for i in range(new_group_start_idx, len(self.garden.plants))
            }
            # Filter out species already in new group
            available = [
                v for v in prioritized_varieties if v.species not in existing_species_in_new_group
            ]
            varieties_to_evaluate = [available[0]] if available else []
        else:
            # Use unique varieties (by signature) to avoid duplicates
            signature_representatives = {}
            for variety in prioritized_varieties:
                sig = self._variety_signature(variety)
                if sig not in signature_representatives:
                    signature_representatives[sig] = variety
            varieties_to_evaluate = list(signature_representatives.values())

        for position in candidates:
            for variety in varieties_to_evaluate:
                if not self.garden.can_place_plant(variety, position):
                    continue

                # Check species constraint for first 3 plants of new group
                if new_group_size < 3:
                    existing_species_in_new_group = {
                        self.garden.plants[i].variety.species
                        for i in range(new_group_start_idx, len(self.garden.plants))
                    }
                    if variety.species in existing_species_in_new_group:
                        continue

                    # For 1st plant: can place anywhere (no other plants to interact with)
                    # For 2nd plant: must interact with 1st plant
                    # For 3rd plant: must interact with 2 different species (both plants in new group)
                    if new_group_size == 0:
                        # 1st plant: no interaction check needed
                        best_value = 999.0
                        best_variety = variety
                        best_position = position
                        break
                    elif new_group_size == 1:
                        # 2nd plant: check if interacts with 1st plant (1 species minimum)
                        new_group_plants = self.garden.plants[new_group_start_idx:]
                        interacting_species = set()
                        for plant in new_group_plants:
                            if plant.variety.species == variety.species:
                                continue
                            dist = (
                                (position.x - plant.position.x) ** 2
                                + (position.y - plant.position.y) ** 2
                            ) ** 0.5
                            if dist < plant.variety.radius + variety.radius:
                                interacting_species.add(plant.variety.species)

                        if len(interacting_species) >= 1:
                            best_value = 999.0
                            best_variety = variety
                            best_position = position
                            break
                        else:
                            # Failed: doesn't interact with 1st plant, skip this position
                            continue
                    elif new_group_size == 2:
                        # 3rd plant: check if interacts with 2 different species in new group
                        new_group_plants = self.garden.plants[new_group_start_idx:]
                        interacting_species = set()
                        for plant in new_group_plants:
                            if plant.variety.species == variety.species:
                                continue
                            dist = (
                                (position.x - plant.position.x) ** 2
                                + (position.y - plant.position.y) ** 2
                            ) ** 0.5
                            if dist < plant.variety.radius + variety.radius:
                                interacting_species.add(plant.variety.species)

                        if len(interacting_species) >= 2:
                            best_value = 999.0
                            best_variety = variety
                            best_position = position
                            break
                        else:
                            # Failed: doesn't interact with 2 species, skip this position
                            continue

                # For 4+ plants: use score function to evaluate placement quality
                adaptive_T = self._get_adaptive_T()
                value, delta, reward = evaluate_placement(
                    self.garden,
                    variety,
                    position,
                    adaptive_T,
                    0.0,  # beta unused (kept for compatibility)
                    self.config['simulation']['w_short'],
                    self.config['simulation']['w_long'],
                    self.current_score,
                )

                if value > best_value:
                    best_value = value
                    best_variety = variety
                    best_position = position

            # For first 3 plants, break after finding first valid position
            if new_group_size < 3 and best_variety is not None:
                break

        # FALLBACK: If no placement found and we can use relaxation (for 4th+ plant)
        # Try allowing 1-species interaction instead of requiring 2-species
        if best_variety is None and new_group_size >= 3 and not relaxation_used:
            if self.config['debug']['verbose']:
                print('    No 2-species placement found. Trying 1-species relaxation...')

            # Re-evaluate all candidates with relaxed constraint (1+ species interaction)
            for position in candidates:
                for variety in varieties_to_evaluate:
                    if not self.garden.can_place_plant(variety, position):
                        continue

                    # Species constraint should not apply here (only for 4+ plants)
                    # (First 3 plants already enforced different species above)

                    # Relaxed constraint: just need to interact with 1+ species (not necessarily 2)
                    if not self._would_interact_with_any_species(variety, position):
                        continue

                    # Evaluate placement with adaptive T
                    adaptive_T = self._get_adaptive_T()
                    value, delta, reward = evaluate_placement(
                        self.garden,
                        variety,
                        position,
                        adaptive_T,
                        0.0,  # beta unused (kept for compatibility)
                        self.config['simulation']['w_short'],
                        self.config['simulation']['w_long'],
                        self.current_score,
                    )

                    if value > best_value:
                        best_value = value
                        best_variety = variety
                        best_position = position
                        used_relaxation = True  # Mark that we used relaxation

        # Map representative back to actual variety instance
        if best_variety is not None and new_group_size >= 3:
            # For 4+ plants: map by signature (to get an actual instance with same params)
            best_sig = self._variety_signature(best_variety)
            for var in self.remaining_varieties:
                if self._variety_signature(var) == best_sig:
                    best_variety = var
                    break

        return best_value, best_variety, best_position, used_relaxation
