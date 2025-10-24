#!/usr/bin/env python3
"""
Launcher for Group 6 Algorithm Visualizer.

This uses the exact same GUI style as the existing project visualizer
but shows our force-directed layout algorithm step by step.

Usage:
    python gardeners/group6/run_algorithm_visualizer.py [config_file] [max_varieties]
    
Examples:
    python gardeners/group6/run_algorithm_visualizer.py
    python gardeners/group6/run_algorithm_visualizer.py config/firstnursery.json 15
    python gardeners/group6/run_algorithm_visualizer.py config/fruits_and_veggies.json 20
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from gardeners.group6.algorithm_visualizer import AlgorithmVisualizer


def load_varieties_from_config(config_file: str, max_varieties: int = 20):
    """Load a limited number of varieties for visualization."""
    config_path = Path(__file__).parent / 'config' / config_file
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    varieties = []
    count = 0
    
    for item in data['varieties']:
        if count >= max_varieties:
            break
            
        variety = PlantVariety(
            name=item['name'],
            radius=item['radius'],
            species=Species[item['species']],
            nutrient_coefficients={
                'R': item['nutrient_coefficients']['R'],
                'G': item['nutrient_coefficients']['G'],
                'B': item['nutrient_coefficients']['B']
            }
        )
        
        # Add limited instances
        instances_to_add = min(item['count'], max_varieties - count)
        for _ in range(instances_to_add):
            varieties.append(variety)
            count += 1
            if count >= max_varieties:
                break
    
    return varieties


def main():
    """Main launcher function."""
    # Default config
    default_config = "config/fruits_and_veggies.json"
    default_max = 20
    
    # Get config file from command line or use default
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = default_config
    
    # Get max varieties from command line or use default
    if len(sys.argv) > 2:
        try:
            max_varieties = int(sys.argv[2])
        except ValueError:
            print(f"Error: Invalid max_varieties '{sys.argv[2]}', using default {default_max}")
            max_varieties = default_max
    else:
        max_varieties = default_max
    
    print(f"Loading varieties from: {config_file}")
    print(f"Max varieties: {max_varieties}")
    
    # Load varieties
    varieties = load_varieties_from_config(config_file, max_varieties)
    if varieties is None:
        return 1
    
    print(f"Loaded {len(varieties)} plant varieties")
    
    # Create and run visualizer
    try:
        visualizer = AlgorithmVisualizer(varieties)
        visualizer.run()
    except KeyboardInterrupt:
        print("\nVisualizer interrupted by user")
    except Exception as e:
        print(f"Error running visualizer: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
