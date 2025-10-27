"""Test runner for Beam Search Gardener."""

import sys
import os
import argparse
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from core.garden import Garden
from core.nursery import Nursery
from core.engine import Engine
from gardeners.group10.beam_search_planting_1026.gardener import BeamSearchGardener


def main():
    parser = argparse.ArgumentParser(description='Test Beam Search Planting Algorithm')
    parser.add_argument('--config', type=str, 
                       default='gardeners/group10/config/test.json',
                       help='Path to variety config file')
    args = parser.parse_args()
    
    # Load varieties from config
    nursery = Nursery()
    varieties = nursery.load_from_file(args.config)
    
    print(f"Loaded {len(varieties)} varieties from {args.config}")
    for variety in varieties:
        print(f"  - {variety.name}: radius={variety.radius}, species={variety.species.name}")
    
    # Analyze nutrient balance
    from core.micronutrients import Micronutrient
    total_R = sum(v.nutrient_coefficients.get(Micronutrient.R, 0.0) for v in varieties)
    total_G = sum(v.nutrient_coefficients.get(Micronutrient.G, 0.0) for v in varieties)
    total_B = sum(v.nutrient_coefficients.get(Micronutrient.B, 0.0) for v in varieties)
    
    print(f"\nNutrient Balance Analysis:")
    print(f"  Net production (if all planted): R={total_R:+.1f}/turn, G={total_G:+.1f}/turn, B={total_B:+.1f}/turn")
    
    depleting = []
    if total_G < 0:
        depleting.append(f"G depletes in ~{int(100/abs(total_G))} turns")
    if total_B < 0:
        depleting.append(f"B depletes in ~{int(100/abs(total_B))} turns")
    if total_R < 0:
        depleting.append(f"R depletes in ~{int(100/abs(total_R))} turns")
    
    if depleting:
        print(f"  ⚠️  WARNING: {', '.join(depleting)}")
        print(f"  Sustained long-term growth is NOT possible with these varieties.")
    print()
    
    # Create garden and gardener
    garden = Garden()
    gardener = BeamSearchGardener(garden, varieties)
    
    # Get T from gardener's config
    turns = gardener.config['simulation']['T']
    
    print(f"Starting beam search placement (using T={turns} turns for scoring)...")
    start_time = time.time()
    
    # Run the placement algorithm
    gardener.cultivate_garden()
    
    placement_time = time.time() - start_time
    print(f"\nPlacement completed in {placement_time:.2f}s")
    print(f"Plants placed: {len(garden.plants)}")
    
    # Run final simulation
    print(f"\nRunning final simulation for {turns} turns...")
    engine = Engine(garden)
    for _ in range(turns):
        engine.run_turn()
    
    final_growth = sum(plant.size for plant in garden.plants)
    
    # Detailed growth pattern analysis
    test_garden = Garden()
    for plant in garden.plants:
        test_garden.add_plant(plant.variety, plant.position)
    
    test_engine = Engine(test_garden)
    
    growth_5 = 0.0
    growth_50 = 0.0
    growth_T = 0.0
    
    for t in range(1, turns + 1):
        test_engine.run_turn()
        current_growth = sum(p.size for p in test_garden.plants)
        
        if t == 5:
            growth_5 = current_growth
        elif t == 50:
            growth_50 = current_growth
        elif t == turns:
            growth_T = current_growth
    
    print(f"\nGrowth Pattern:")
    print(f"  Turn 5: {growth_5}")
    if turns >= 50:
        print(f"  Turn 50: {growth_50}")
    print(f"  Turn {turns}: {growth_T}")
    print(f"  Growth after turn 5: {growth_T - growth_5}")
    
    # Print results
    print("\n" + "="*50)
    print("RESULTS")
    print("="*50)
    print(f"Final Total Growth: {final_growth:.2f}")
    if len(garden.plants) > 0:
        print(f"Average Growth per Plant: {final_growth / len(garden.plants):.2f}")
    print(f"Plants Placed: {len(garden.plants)}")
    print(f"Placement Time: {placement_time:.2f}s")
    print(f"Simulation Turns (T): {turns}")
    
    # Print plant details with interactions
    print(f"\nPlant Details:")
    for i, plant in enumerate(garden.plants, 1):
        # Count interactions
        interactions = []
        for other in garden.plants:
            if plant == other:
                continue
            if plant.variety.species != other.variety.species:
                dist = ((plant.position.x - other.position.x)**2 + 
                       (plant.position.y - other.position.y)**2) ** 0.5
                interaction_dist = plant.variety.radius + other.variety.radius
                if dist < interaction_dist:
                    interactions.append(other.variety.name[:10])
        
        growth_pct = (plant.size / plant.variety.radius - 1) * 100
        print(f"  {i}. {plant.variety.name}: size={plant.size}, growth={growth_pct:.1f}%, "
              f"pos=({plant.position.x}, {plant.position.y}), "
              f"interacts_with={len(interactions)} {interactions}")


if __name__ == '__main__':
    main()

