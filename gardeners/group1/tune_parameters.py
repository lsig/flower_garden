"""
Parameter tuning script for Gardener1 algorithm.
Tests different parameter combinations across all config files to maximize total growth.
"""

import itertools
import json
import random
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.engine import Engine
from core.garden import Garden
from core.nursery import Nursery
from gardeners.group1.gardener import Gardener1

# Find all config files
CONFIG_DIRS = [
    Path('gardeners/group1/config'),
    Path('gardeners/group2/config'),
    Path('gardeners/group3/config'),
    Path('gardeners/group4/config'),
    Path('gardeners/group5/config'),
    Path('gardeners/group6/config'),
    Path('gardeners/group7/configs'),
    Path('gardeners/group8/config'),
    Path('gardeners/group9/config'),
    Path('gardeners/group10/config'),
]


def get_all_config_files():
    """Find all JSON config files."""
    config_files = []
    for config_dir in CONFIG_DIRS:
        if config_dir.exists():
            config_files.extend(config_dir.glob('*.json'))
    return sorted(config_files)


def test_parameters(params, config_files, turns=100, max_configs=None):
    """Test a parameter set on config files."""
    total_growth = 0.0
    total_plants = 0
    successful_runs = 0
    times = []

    # Limit configs for faster testing
    test_configs = config_files[:max_configs] if max_configs else config_files

    for config_file in test_configs:
        try:
            nursery = Nursery()
            varieties = nursery.load_from_file(str(config_file))

            garden = Garden()
            # Create gardener with these parameters
            gardener = Gardener1(garden, varieties, params=params)

            # Run cultivation
            start_time = time.time()
            gardener.cultivate_garden()
            placement_time = time.time() - start_time

            if placement_time > 60:
                print(f'  WARNING: {config_file.name} exceeded time limit ({placement_time:.1f}s)')
                continue

            # Run simulation
            engine = Engine(garden)
            engine.run_simulation(turns=turns)

            growth = garden.total_growth()
            plants = len(garden.plants)

            total_growth += growth
            total_plants += plants
            successful_runs += 1
            times.append(placement_time)

        except Exception as e:
            print(f'  ERROR on {config_file.name}: {e}')
            continue

    if successful_runs == 0:
        return 0.0, 0, 0.0, 0.0

    avg_growth = total_growth / successful_runs
    avg_plants = total_plants / successful_runs
    avg_time = sum(times) / len(times)

    return avg_growth, successful_runs, avg_plants, avg_time


def grid_search_parameters(config_files, max_combinations=20, turns=50, max_configs=10):
    """Perform grid search over parameter space."""
    print(f'Testing on {len(config_files)} config files')
    print(f'Using {max_configs} configs per test, {turns} turns per simulation')
    print(f'Testing {max_combinations} combinations for speed\n')

    # Key parameters to optimize (reduced space for 5-minute runtime)
    key_params = {
        'min_sufficiency_weight': [15.0, 20.0, 25.0],  # 3 values
        'species_bonus_weight': [5.0, 7.0, 10.0],  # 3 values
        'cross_species_weight': [12.0, 16.0, 20.0],  # 3 values
        'optimal_distance_weight': [2.0, 2.5, 3.0],  # 3 values
    }

    best_params = None
    best_score = -1
    results = []

    # Generate combinations
    param_names = list(key_params.keys())
    param_values = [key_params[name] for name in param_names]

    combinations = list(itertools.product(*param_values))
    total_combos = min(len(combinations), max_combinations)

    print(f'Testing {total_combos} parameter combinations...\n')

    for i, combo in enumerate(combinations[:max_combinations]):
        params = dict(zip(param_names, combo, strict=False))
        # Fill in defaults for other parameters
        params.update(
            {
                'growth_efficiency_weight': 2.0,
                'base_score_weight': 1.0,
                'exchange_potential_weight': 0.5,
                'min_distance_weight': 1.5,
                'radius_weight': 1.0,
                'species_bonus_all': 20.0,
                'species_bonus_two': 5.0,
                'balance_penalty_multiplier': 2.0,
                'partner_penalty_multiplier': 2.0,
            }
        )

        print(f'[{i + 1}/{total_combos}] Testing parameters...')
        print(
            f'  min_suff={params["min_sufficiency_weight"]}, '
            f'species_bonus={params["species_bonus_weight"]}, '
            f'cross_species={params["cross_species_weight"]}, '
            f'opt_dist={params["optimal_distance_weight"]}'
        )

        score, runs, avg_plants, avg_time = test_parameters(
            params, config_files, turns=turns, max_configs=max_configs
        )

        print(
            f'  Result: Growth={score:.2f}, Runs={runs}, Plants={avg_plants:.1f}, Time={avg_time:.2f}s'
        )

        if score > best_score:
            best_score = score
            best_params = params.copy()
            print(f'  *** NEW BEST! Score: {score:.2f} ***')

        results.append((params.copy(), score, runs, avg_plants, avg_time))
        print()

    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)

    print('=' * 70)
    print('TOP 10 PARAMETER COMBINATIONS:')
    print('=' * 70)
    for i, (params, score, runs, plants, time_taken) in enumerate(results[:10]):
        print(
            f'\n{i + 1}. Score: {score:.2f} (Runs: {runs}, Plants: {plants:.1f}, Time: {time_taken:.2f}s)'
        )
        print(f'   min_sufficiency_weight: {params["min_sufficiency_weight"]}')
        print(f'   species_bonus_weight: {params["species_bonus_weight"]}')
        print(f'   cross_species_weight: {params["cross_species_weight"]}')
        print(f'   optimal_distance_weight: {params["optimal_distance_weight"]}')

    return best_params, results


def random_search_parameters(config_files, n_iterations=50, turns=100, max_configs=25):
    """Random search for faster exploration."""
    print(f'Random search: {n_iterations} iterations')
    print(f'Using {max_configs} configs per test, {turns} turns per simulation\n')

    param_ranges = {
        'min_sufficiency_weight': (10.0, 30.0),
        'species_bonus_weight': (2.0, 12.0),
        'growth_efficiency_weight': (1.0, 4.0),
        'base_score_weight': (0.5, 2.0),
        'exchange_potential_weight': (0.3, 1.5),
        'cross_species_weight': (8.0, 25.0),
        'optimal_distance_weight': (1.0, 4.0),
        'min_distance_weight': (1.0, 3.0),
        'radius_weight': (0.5, 2.0),
        'species_bonus_all': (15.0, 35.0),
        'species_bonus_two': (3.0, 10.0),
        'balance_penalty_multiplier': (1.0, 3.0),
        'partner_penalty_multiplier': (1.0, 3.0),
    }

    best_params = None
    best_score = -1
    results = []

    for i in range(n_iterations):
        # Random sample
        params = {}
        for key, (min_val, max_val) in param_ranges.items():
            params[key] = random.uniform(min_val, max_val)

        print(f'[{i + 1}/{n_iterations}] Testing random parameters...')

        score, runs, avg_plants, avg_time = test_parameters(
            params, config_files, turns=turns, max_configs=max_configs
        )

        print(
            f'  Result: Growth={score:.2f}, Runs={runs}, Plants={avg_plants:.1f}, Time={avg_time:.2f}s'
        )

        if score > best_score:
            best_score = score
            best_params = params.copy()
            print(f'  *** NEW BEST! Score: {score:.2f} ***')

        results.append((params.copy(), score, runs, avg_plants, avg_time))
        print()

    results.sort(key=lambda x: x[1], reverse=True)

    print('=' * 70)
    print('TOP 10 PARAMETER COMBINATIONS:')
    print('=' * 70)
    for i, (params, score, runs, plants, time_taken) in enumerate(results[:10]):
        print(
            f'\n{i + 1}. Score: {score:.2f} (Runs: {runs}, Plants: {plants:.1f}, Time: {time_taken:.2f}s)'
        )
        for key in sorted(params.keys()):
            print(f'   {key}: {params[key]:.2f}')

    return best_params, results


if __name__ == '__main__':
    config_files = get_all_config_files()
    print(f'Found {len(config_files)} config files\n')

    # Run grid search (more systematic)
    print('=' * 70)
    print('GRID SEARCH (Optimized for ~5 minute runtime)')
    print('=' * 70)
    best_params_grid, grid_results = grid_search_parameters(
        config_files, max_combinations=20, turns=50, max_configs=10
    )

    print('\n' + '=' * 70)
    print('BEST PARAMETERS (Grid Search):')
    print('=' * 70)
    print(json.dumps(best_params_grid, indent=2))

    # Save best parameters to file
    output_file = Path(__file__).parent / 'best_params.json'
    with open(output_file, 'w') as f:
        json.dump(best_params_grid, f, indent=2)
    print(f'\nBest parameters saved to: {output_file}')
