"""Standalone test runner for Greedy Planting Algorithm."""

import argparse
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from core.garden import Garden
from core.engine import Engine
from core.nursery import Nursery
from gardeners.group10.greedy_algorithm_with_replacement_1027.gardener import GreedyGardener


def main():
    parser = argparse.ArgumentParser(description='Test Greedy Planting Algorithm')
    parser.add_argument('--config', required=True, help='Path to nursery JSON config file')
    parser.add_argument('--gui', action='store_true', help='Enable GUI visualization')
    parser.add_argument('--turns', type=int, default=None, help='Number of simulation turns (defaults to config T)')
    
    args = parser.parse_args()
    
    # Load varieties from config
    nursery = Nursery()
    varieties = nursery.load_from_file(args.config)
    
    print(f"Loaded {len(varieties)} varieties from {args.config}")
    for variety in varieties:
        print(f"  - {variety.name}: radius={variety.radius}, species={variety.species.name}")
    print()
    
    # Create garden and gardener with optional simulation_turns
    garden = Garden()
    gardener = GreedyGardener(garden, varieties, simulation_turns=args.turns)
    
    # Get actual T used (will be min(args.turns, config_T) if args.turns provided)
    turns = gardener.config['simulation']['T']
    
    # Time the placement
    print(f"Starting plant placement (using T={turns} turns for scoring)...")
    import time
    start_time = time.time()
    gardener.cultivate_garden()
    placement_time = time.time() - start_time
    
    print(f"\nPlacement completed in {placement_time:.2f}s")
    print(f"Plants placed: {len(garden.plants)}")
    
    if placement_time > 60.0:
        print(f"WARNING: Placement exceeded time limit ({placement_time:.2f}s > 60.0s)")
    
    # Run final simulation with same T
    print(f"\nRunning final simulation for {turns} turns...")
    engine = Engine(garden)
    engine.run_simulation(turns=turns)
    
    # Analyze growth pattern
    if len(engine.growth_history) > 0:
        early_growth = engine.growth_history[4] if len(engine.growth_history) > 4 else engine.growth_history[-1]
        mid_growth = engine.growth_history[49] if len(engine.growth_history) > 49 else engine.growth_history[-1]
        final_growth_val = engine.growth_history[-1]
        print(f"\nGrowth Pattern:")
        print(f"  Turn 5: {early_growth:.1f}")
        print(f"  Turn 50: {mid_growth:.1f}")
        print(f"  Turn {turns}: {final_growth_val:.1f}")
        print(f"  Growth after turn 5: {final_growth_val - early_growth:.1f}")
        
        # Check for sustained growth
        if len(engine.growth_history) >= 20:
            growth_5_to_10 = engine.growth_history[9] - engine.growth_history[4]
            growth_10_to_20 = engine.growth_history[19] - engine.growth_history[9]
            print(f"  Growth rate (turns 5-10): {growth_5_to_10:.1f}")
            print(f"  Growth rate (turns 10-20): {growth_10_to_20:.1f}")
            
            if growth_10_to_20 > 0:
                print("  Status: SUSTAINED GROWTH detected")
            else:
                print("  Status: Growth stalled")
    
    # Print test summary
    final_growth = garden.total_growth()
    avg_growth = final_growth / len(garden.plants) if len(garden.plants) > 0 else 0.0
    
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Growth:        {final_growth:.2f}")
    print(f"Plants Placed:       {len(garden.plants)}/{len(varieties)}")
    print(f"Average per Plant:   {avg_growth:.2f}")
    print(f"Placement Time:      {placement_time:.2f}s")
    print(f"Simulation Turns:    {turns}")
    
    # Print detailed analysis (after simulation)
    if gardener.config['debug']['verbose']:
        gardener.print_final_analysis()
    
    # Run GUI if requested
    if args.gui:
        from core.ui.visualizer import GardenVisualizer
        print("\nLaunching GUI...")
        visualizer = GardenVisualizer(
            garden,
            engine,
            "GreedyGardener",
            turns=turns
        )
        visualizer.run()


if __name__ == '__main__':
    main()
