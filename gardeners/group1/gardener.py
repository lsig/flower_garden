import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError, wait

from core.engine import Engine
from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety


def _run_strategy_worker(strategy_name, garden_width, garden_height, varieties_data, params):
    """
    Worker function to run a single strategy in a separate process.
    Returns: (strategy_name, score, plant_placements) or None if failed
    """
    try:
        from core.micronutrients import Micronutrient
        from core.plants.species import Species

        # Import strategy class
        if strategy_name == 'fixed_k':
            from gardeners.group1.gardener_fixed_k import Gardener1f as StrategyClass
        elif strategy_name == 'hybrid':
            from gardeners.group1.gardener_hybrid import Gardener1h as StrategyClass
        elif strategy_name == 'mixed_k':
            from gardeners.group1.gardener_mixed_k import Gardener1m as StrategyClass
        elif strategy_name == 'prev':
            from gardeners.group1.gardener_prev import Gardener1Prev as StrategyClass
        else:
            return None

        # Reconstruct PlantVariety objects from serialized data
        varieties = []
        for v_data in varieties_data:
            species = Species[v_data['species']]
            nutrient_coefficients = {
                Micronutrient[nut_name]: coef
                for nut_name, coef in v_data['nutrient_coefficients'].items()
            }
            variety = PlantVariety(
                name=v_data['name'],
                radius=v_data['radius'],
                species=species,
                nutrient_coefficients=nutrient_coefficients,
            )
            varieties.append(variety)

        # Create test garden
        test_garden = Garden(garden_width, garden_height)

        # Run strategy
        gardener = StrategyClass(test_garden, varieties, params)
        gardener.cultivate_garden()

        # Simulate to measure final growth
        engine = Engine(test_garden)
        engine.run_simulation(turns=100)

        # Get results
        score = test_garden.total_growth()

        # Serialize placements (variety attributes + position)
        placements = []
        for plant in test_garden.plants:
            v = plant.variety
            placement = {
                'name': v.name,
                'radius': v.radius,
                'species': v.species.name,
                'nutrient_coefficients': {
                    nut.name: coef for nut, coef in v.nutrient_coefficients.items()
                },
                'position': (plant.position.x, plant.position.y),
            }
            placements.append(placement)

        return (strategy_name, score, placements)

    except Exception:
        # Return error for debugging
        return (strategy_name, -1, [])  # Negative score indicates failure


class Gardener1(Gardener):
    """
    META-STRATEGY: Run 3 best strategies IN PARALLEL and pick the best one.

    Strategies tested (simultaneously):
    1. Fixed-K: All groups same size (proven baseline)
    2. Hybrid: Fixed-K + post-optimization
    3. Mixed-K: Each group can have different size

    Approach:
    - Launch all 3 strategies in parallel processes
    - Each runs independently with deadline tracking
    - Pick strategy with highest growth
    - Apply winner's placements to actual garden
    - Total time = max(strategy_times) instead of sum
    - Hard deadline at 55s to ensure we finish before 60s limit
    """

    def __init__(self, garden: Garden, varieties: list[PlantVariety], params: dict | None = None):
        super().__init__(garden, varieties)
        self.params = params

    def cultivate_garden(self):
        """
        Meta-strategy: Run all 4 approaches IN PARALLEL and pick the best.
        """
        start_time = time.time()
        hard_deadline = start_time + 55.0  # Must finish by 55s, leave 5s buffer

        # Serialize varieties for multiprocessing (avoid pickling issues)
        varieties_data = []
        for v in self.varieties:
            v_data = {
                'name': v.name,
                'radius': v.radius,
                'species': v.species.name,
                'nutrient_coefficients': {
                    nut.name: coef for nut, coef in v.nutrient_coefficients.items()
                },
            }
            varieties_data.append(v_data)

        # Define strategies to test
        # Note: 'prev' excluded as it can timeout on large configs
        strategies = ['fixed_k', 'hybrid', 'mixed_k']

        results = {}

        # Run strategies in parallel using ProcessPoolExecutor
        # Use 'fork' context on Unix for better compatibility
        mp_context = multiprocessing.get_context('fork') if sys.platform != 'win32' else None
        with ProcessPoolExecutor(max_workers=3, mp_context=mp_context) as executor:
            # Submit all strategies
            futures = {
                executor.submit(
                    _run_strategy_worker,
                    strategy_name,
                    self.garden.width,
                    self.garden.height,
                    varieties_data,
                    self.params,
                ): strategy_name
                for strategy_name in strategies
            }

            # Collect results as they complete, respecting hard deadline
            pending = set(futures.keys())

            while pending and (time.time() < hard_deadline - 2.0):
                # Calculate how much time we have left
                time_left = hard_deadline - time.time() - 1.0
                if time_left <= 0:
                    break

                try:
                    # Wait for futures to complete, with timeout based on remaining time
                    done, pending = wait(
                        pending, timeout=min(time_left, 5.0), return_when='FIRST_COMPLETED'
                    )

                    # Process completed futures
                    for future in done:
                        try:
                            result = future.result(timeout=0.1)
                            if result:
                                strategy_name, score, placements = result
                                # Skip strategies that failed (negative score)
                                if score > 0:
                                    results[strategy_name] = {
                                        'score': score,
                                        'placements': placements,
                                    }
                        except (TimeoutError, Exception):
                            pass

                except (TimeoutError, Exception):
                    # Timeout or error - use whatever results we have
                    break

        # If no strategies succeeded, use fallback (just place largest plants)
        if not results:
            self._fallback_strategy()
            return

        # Pick best strategy based on growth
        best_strategy = max(results.keys(), key=lambda k: results[k]['score'])
        best_result = results[best_strategy]

        # Apply winner's placements to actual garden
        from core.micronutrients import Micronutrient
        from core.plants.species import Species
        from core.point import Position

        # Track which varieties have been used (by index in self.varieties list)
        used_variety_indices = set()

        for placement_dict in best_result['placements']:
            # Reconstruct species and nutrients from serialized data
            species = Species[placement_dict['species']]
            nutrient_coefficients = {
                Micronutrient[nut_name]: coef
                for nut_name, coef in placement_dict['nutrient_coefficients'].items()
            }

            # Find matching variety from our list (same species, radius, nutrients)
            # that hasn't been used yet
            matching_variety = None
            matching_index = None
            for idx, v in enumerate(self.varieties):
                if idx in used_variety_indices:
                    continue  # Skip already used varieties

                if v.species == species and v.radius == placement_dict['radius']:
                    # Check nutrient coefficients match
                    nutrients_match = True
                    for nut, coef in v.nutrient_coefficients.items():
                        if abs(nutrient_coefficients.get(nut, 0) - coef) > 0.001:
                            nutrients_match = False
                            break
                    if nutrients_match:
                        matching_variety = v
                        matching_index = idx
                        break

            if matching_variety:
                x, y = placement_dict['position']
                pos = Position(x, y)
                if self.garden.can_place_plant(matching_variety, pos):
                    self.garden.add_plant(matching_variety, pos)
                    used_variety_indices.add(matching_index)  # Mark as used

    def _fallback_strategy(self):
        """
        Emergency fallback if all strategies fail.
        Just place the largest plants in a simple grid.
        """
        # Sort by radius (largest first)
        sorted_varieties = sorted(self.varieties, key=lambda v: v.radius, reverse=True)

        # Simple grid placement
        from core.point import Position

        spacing = 10.0
        x, y = spacing, spacing

        for variety in sorted_varieties:
            if x > self.garden.width - spacing:
                x = spacing
                y += spacing
                if y > self.garden.height - spacing:
                    break

            pos = Position(x, y)
            if self.garden.can_place_plant(variety, pos):
                self.garden.add_plant(variety, pos)
            x += spacing
