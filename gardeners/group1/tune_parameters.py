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
    # Exclude best_params.json (not a config file)
    config_files = [f for f in config_files if f.name != 'best_params.json']
    return sorted(config_files)


def test_parameters(params, config_files, turns=100, max_configs=None):
    """Test a parameter set on config files."""
    total_growth = 0.0
    total_plants = 0
    successful_runs = 0
    times = []

    # Use all configs if max_configs is None, otherwise limit
    test_configs = config_files[:max_configs] if max_configs is not None else config_files

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


def grid_search_parameters(config_files, max_combinations=200, turns=100, max_configs=None):
    """Perform comprehensive grid search over parameter space."""
    config_count = max_configs if max_configs is not None else len(config_files)
    print(f'Testing on {len(config_files)} total config files')
    print(f'Using {config_count} configs per test, {turns} turns per simulation')
    print(f'Testing up to {max_combinations} combinations\n')

    # Expanded parameter space for comprehensive search
    key_params = {
        # Core group evaluation parameters
        'min_sufficiency_weight': [10.0, 15.0, 20.0, 25.0, 30.0],  # 5 values
        'species_bonus_weight': [3.0, 5.0, 7.0, 10.0, 12.0],  # 5 values
        'growth_efficiency_weight': [1.0, 1.5, 2.0, 2.5, 3.0],  # 5 values
        'base_score_weight': [0.5, 1.0, 1.5, 2.0],  # 4 values
        'exchange_potential_weight': [0.3, 0.5, 0.7, 1.0],  # 4 values
        
        # Species diversity bonuses
        'species_bonus_all': [15.0, 20.0, 25.0, 30.0, 35.0],  # 5 values
        'species_bonus_two': [3.0, 5.0, 7.0, 10.0],  # 4 values
        
        # Placement parameters
        'cross_species_weight': [8.0, 12.0, 16.0, 20.0, 24.0],  # 5 values
        'optimal_distance_weight': [1.5, 2.0, 2.5, 3.0, 3.5],  # 5 values
        'min_distance_weight': [1.0, 1.5, 2.0, 2.5],  # 4 values
        'radius_weight': [0.5, 1.0, 1.5, 2.0],  # 4 values
        
        # Penalty parameters
        'balance_penalty_multiplier': [1.0, 1.5, 2.0, 2.5, 3.0],  # 5 values
        'partner_penalty_multiplier': [1.0, 1.5, 2.0, 2.5, 3.0],  # 5 values
    }

    best_params = None
    best_score = -1
    results = []

    # Generate all combinations
    param_names = list(key_params.keys())
    param_values = [key_params[name] for name in param_names]

    combinations = list(itertools.product(*param_values))
    total_combos = len(combinations)
    print(f'Total possible combinations: {total_combos}')
    
    # If too many, use random sampling
    if total_combos > max_combinations:
        print(f'Randomly sampling {max_combinations} combinations from {total_combos} total\n')
        combinations = random.sample(combinations, max_combinations)
        total_combos = max_combinations
    else:
        print(f'Testing all {total_combos} parameter combinations...\n')

    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo, strict=False))
        # All parameters are now in key_params, no need to fill defaults

        print(f'[{i + 1}/{total_combos}] Testing parameters...')
        # Print key parameters for brevity
        print(
            f'  min_suff={params["min_sufficiency_weight"]:.1f}, '
            f'species_bonus={params["species_bonus_weight"]:.1f}, '
            f'cross_species={params["cross_species_weight"]:.1f}, '
            f'opt_dist={params["optimal_distance_weight"]:.1f}'
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
            
            # Save incrementally to file
            output_file = Path(__file__).parent / 'best_params.json'
            incremental_data = {
                'best_parameters': best_params.copy(),
                'best_score': best_score,
                'runs': runs,
                'avg_plants': avg_plants,
                'avg_time': avg_time,
                'combination_number': i + 1,
                'search_type': 'grid_search'
            }
            with open(output_file, 'w') as f:
                json.dump(incremental_data, f, indent=2)
            print(f'  Saved to {output_file}')

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
        for key in sorted(params.keys()):
            print(f'   {key}: {params[key]:.2f}')

    return best_params, results


def random_search_parameters(config_files, n_iterations=200, turns=100, max_configs=None):
    """Random search for faster exploration of large parameter space."""
    config_count = max_configs if max_configs is not None else len(config_files)
    print(f'Random search: {n_iterations} iterations')
    print(f'Using {config_count} configs per test, {turns} turns per simulation\n')

    param_ranges = {
        'min_sufficiency_weight': (8.0, 35.0),
        'species_bonus_weight': (2.0, 15.0),
        'growth_efficiency_weight': (0.5, 4.0),
        'base_score_weight': (0.3, 2.5),
        'exchange_potential_weight': (0.2, 1.5),
        'cross_species_weight': (6.0, 28.0),
        'optimal_distance_weight': (1.0, 4.5),
        'min_distance_weight': (0.5, 3.0),
        'radius_weight': (0.3, 2.5),
        'species_bonus_all': (12.0, 40.0),
        'species_bonus_two': (2.0, 12.0),
        'balance_penalty_multiplier': (0.5, 3.5),
        'partner_penalty_multiplier': (0.5, 3.5),
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
            
            # Save incrementally to file
            output_file = Path(__file__).parent / 'best_params.json'
            incremental_data = {
                'best_parameters': best_params.copy(),
                'best_score': best_score,
                'runs': runs,
                'avg_plants': avg_plants,
                'avg_time': avg_time,
                'iteration_number': i + 1,
                'search_type': 'random_search'
            }
            with open(output_file, 'w') as f:
                json.dump(incremental_data, f, indent=2)
            print(f'  Saved to {output_file}')

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

    # Calculate estimated time
    # Rough estimate: ~2-5 seconds per config file (placement + 100 turns simulation)
    # This is conservative - actual time depends on config complexity
    total_configs = len(config_files)
    total_combinations = 200 + 200  # grid + random
    estimated_seconds = total_configs * total_combinations * 3  # ~3 sec per config per combination
    estimated_hours = estimated_seconds / 3600
    estimated_minutes = (estimated_seconds % 3600) / 60
    
    print(f'Estimated runtime: ~{estimated_hours:.1f} hours ({estimated_minutes:.0f} minutes)')
    print(f'This is based on testing {total_combinations} combinations on {total_configs} config files')
    print('Note: Actual time may vary based on config complexity')
    print('Starting full parameter sweep...\n')

    # Run comprehensive grid search on ALL configs
    print('=' * 70)
    print('COMPREHENSIVE GRID SEARCH (All Configs)')
    print('=' * 70)
    best_params_grid, grid_results = grid_search_parameters(
        config_files, max_combinations=200, turns=100, max_configs=None  # None = all configs
    )

    print('\n' + '=' * 70)
    print('BEST PARAMETERS (Grid Search):')
    print('=' * 70)
    print(json.dumps(best_params_grid, indent=2))

    # Run random search for additional exploration on ALL configs
    print('\n' + '=' * 70)
    print('RANDOM SEARCH (Additional Exploration - All Configs)')
    print('=' * 70)
    best_params_random, random_results = random_search_parameters(
        config_files, n_iterations=200, turns=100, max_configs=None  # None = all configs
    )

    # Combine results from both searches
    all_results = grid_results + random_results
    all_results.sort(key=lambda x: x[1], reverse=True)  # Sort by score
    
    # Get top 5 parameter sets
    top_n = 5
    top_params = []
    for i, (params, score, runs, plants, time_taken) in enumerate(all_results[:top_n]):
        top_params.append({
            'rank': i + 1,
            'score': score,
            'runs': runs,
            'avg_plants': plants,
            'avg_time': time_taken,
            'parameters': params
        })
    
    # Compare and pick absolute best
    if best_params_random and best_params_grid:
        grid_score = max([r[1] for r in grid_results]) if grid_results else 0
        random_score = max([r[1] for r in random_results]) if random_results else 0
        
        if random_score > grid_score:
            best_params = best_params_random
            best_score = random_score
            print(f'\nRandom search found better parameters: {best_score:.2f} vs {grid_score:.2f}')
        else:
            best_params = best_params_grid
            best_score = grid_score
            print(f'\nGrid search found better parameters: {best_score:.2f} vs {random_score:.2f}')
    else:
        best_params = best_params_grid or best_params_random

    # Save top N parameter sets to file
    output_file = Path(__file__).parent / 'best_params.json'
    output_data = {
        'best_parameters': best_params,
        'best_score': all_results[0][1] if all_results else 0,
        'top_parameter_sets': top_params
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f'\nTop {top_n} parameter sets saved to: {output_file}')
    
    print('\n' + '=' * 70)
    print('FINAL BEST PARAMETERS:')
    print('=' * 70)
    print(json.dumps(best_params, indent=2))
    
    print('\n' + '=' * 70)
    print(f'TOP {top_n} PARAMETER SETS:')
    print('=' * 70)
    for i, entry in enumerate(top_params[:top_n]):
        print(f'\nRank {entry["rank"]}: Score={entry["score"]:.2f} (Runs={entry["runs"]}, Plants={entry["avg_plants"]:.1f})')
        print(json.dumps(entry["parameters"], indent=2))
