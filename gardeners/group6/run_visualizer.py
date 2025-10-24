#!/usr/bin/env python3
"""
Launcher script for Group 6 Algorithm Visualizer.

Usage:
    python gardeners/group6/run_visualizer.py [config_file]
    
Examples:
    python gardeners/group6/run_visualizer.py
    python gardeners/group6/run_visualizer.py config/firstnursery.json
    python gardeners/group6/run_visualizer.py config/fruits_and_veggies.json
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from gardeners.group6.visualizer import Group6Visualizer


def load_varieties_from_config(config_file: str):
    """Load plant varieties from a JSON config file."""
    # Handle both relative and absolute paths
    if config_file.startswith('config/'):
        config_path = Path(__file__).parent / config_file
    else:
        config_path = Path(__file__).parent / 'config' / config_file
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    varieties = []
    for item in data['varieties']:
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
        # Add multiple instances based on count
        for _ in range(item['count']):
            varieties.append(variety)
    
    return varieties


def main():
    """Main launcher function."""
    # Default config
    default_config = "config/fruits_and_veggies.json"
    
    # Get config file from command line or use default
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = default_config
    
    print(f"Loading varieties from: {config_file}")
    
    # Load varieties
    varieties = load_varieties_from_config(config_file)
    if varieties is None:
        return 1
    
    print(f"Loaded {len(varieties)} plant varieties")
    
    # Create and run visualizer
    try:
        visualizer = Group6Visualizer(varieties)
        visualizer.run()
    except KeyboardInterrupt:
        print("\nVisualizer interrupted by user")
    except Exception as e:
        print(f"Error running visualizer: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
