"""Beam Search Planting Algorithm with Diversity Bonus."""

import os
import yaml
import copy
from typing import List, Dict, Tuple, Optional

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position
from core.micronutrients import Micronutrient

from gardeners.group10.beam_search_planting_1026.utils import (
    generate_grid_candidates,
    generate_geometric_candidates,
    filter_candidates,
    geometric_heuristic,
    evaluate_placement,
    simulate_and_score,
    calculate_diversity_bonus,
)


class BeamSearchGardener(Gardener):
    """Beam search planting algorithm with diversity bonus."""
    
    def __init__(self, garden: Garden, varieties: List[PlantVariety]):
        super().__init__(garden, varieties)
        self.config = self._load_config()
        self.all_varieties = varieties.copy()
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            'config.yaml'
        )
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def cultivate_garden(self) -> None:
        """
        Main placement loop using beam search:
        - Maintain k best partial solutions (beam)
        - At each step, expand each beam state with all possible placements
        - Keep top k expanded states (with diversity bonus)
        - Return the best complete solution
        """
        beam_width = self.config['beam']['width']
        diversity_weight = self.config['beam']['diversity_weight']
        pruning_threshold = self.config['beam']['pruning_threshold']
        
        if self.config['debug']['verbose']:
            print(f"Starting beam search with width={beam_width}, diversity_weight={diversity_weight}")
        
        # Initialize beam with empty state
        beam = [{
            'garden': Garden(),
            'varieties': self.all_varieties.copy(),
            'score': 0.0,
            'history': []
        }]
        
        iteration = 0
        
        while True:
            iteration += 1
            
            if self.config['debug']['verbose']:
                print(f"\n=== Iteration {iteration} ===")
                print(f"Beam size: {len(beam)}")
                for i, state in enumerate(beam):
                    print(f"  State {i}: {len(state['garden'].plants)} plants, score={state['score']:.4f}")
            
            # Check if all beam states are complete (no more varieties)
            all_complete = all(len(state['varieties']) == 0 for state in beam)
            if all_complete:
                if self.config['debug']['verbose']:
                    print("All beam states are complete")
                break
            
            # Expand each beam state
            expanded_states = []
            
            for state_idx, state in enumerate(beam):
                if len(state['varieties']) == 0:
                    # This state is complete, keep as is
                    expanded_states.append(state)
                    continue
                
                # Generate candidates for this state
                candidates = self._generate_candidates(state['garden'])
                
                if self.config['debug']['verbose']:
                    print(f"  Generated {len(candidates)} candidates for state {state_idx}")
                
                if not candidates:
                    # No valid candidates, this state cannot be expanded further
                    if self.config['debug']['verbose']:
                        print(f"  No candidates for state {state_idx}, keeping as is")
                    expanded_states.append(state)
                    continue
                
                # Prune candidates
                pruned_candidates = self._prune_candidates(state['garden'], candidates, state['varieties'])
                
                if self.config['debug']['verbose']:
                    print(f"  After pruning: {len(pruned_candidates)} candidates for state {state_idx}")
                
                if not pruned_candidates:
                    # No candidates after pruning
                    if self.config['debug']['verbose']:
                        print(f"  No candidates after pruning for state {state_idx}")
                    expanded_states.append(state)
                    continue
                
                # Get prioritized varieties
                prioritized_varieties = self._get_nutrient_priorities(state['garden'], state['varieties'])
                
                if self.config['debug']['verbose']:
                    print(f"  Trying {len(prioritized_varieties)} varieties for state {state_idx}")
                
                # Try placing each variety at each candidate position
                placements_tried = 0
                placements_can_place = 0
                placements_successful = 0
                for variety in prioritized_varieties:
                    for position in pruned_candidates:
                        placements_tried += 1
                        # Check if we can place
                        if not state['garden'].can_place_plant(variety, position):
                            continue
                        
                        placements_can_place += 1
                        # Create new state with this placement
                        new_state = self._expand_state(state, variety, position)
                        
                        if new_state is not None:
                            placements_successful += 1
                            expanded_states.append(new_state)
                
                if self.config['debug']['verbose']:
                    print(f"  State {state_idx}: tried {placements_tried} placements, {placements_can_place} passed can_place, {placements_successful} successful")
            
            if not expanded_states:
                if self.config['debug']['verbose']:
                    print("No valid expansions found, stopping")
                break
            
            # Score all expanded states (including diversity bonus)
            for state in expanded_states:
                base_score = state['score']
                diversity_bonus = calculate_diversity_bonus(expanded_states, state, diversity_weight)
                state['total_score'] = base_score + diversity_bonus
                state['diversity_bonus'] = diversity_bonus
            
            # Sort by total score (descending)
            expanded_states.sort(key=lambda s: s['total_score'], reverse=True)
            
            # Prune states below threshold
            if len(expanded_states) > beam_width:
                best_score = expanded_states[0]['total_score']
                threshold = best_score * pruning_threshold
                expanded_states = [s for s in expanded_states if s['total_score'] >= threshold]
            
            # Keep top k states
            beam = expanded_states[:beam_width]
            
            if self.config['debug']['verbose']:
                print(f"After expansion and pruning: {len(beam)} states")
                for i, state in enumerate(beam[:3]):  # Show top 3
                    print(f"  State {i}: {len(state['garden'].plants)} plants, "
                          f"score={state['score']:.4f}, diversity={state.get('diversity_bonus', 0):.4f}, "
                          f"total={state['total_score']:.4f}")
        
        # Select best final state
        best_state = max(beam, key=lambda s: s['score'])
        
        if self.config['debug']['verbose']:
            print(f"\n=== Best Solution ===")
            print(f"Plants: {len(best_state['garden'].plants)}")
            print(f"Score: {best_state['score']:.4f}")
        
        # Apply best solution to our garden
        for plant in best_state['garden'].plants:
            self.garden.add_plant(plant.variety, plant.position)
    
    def _generate_candidates(self, garden: Garden) -> List[Position]:
        """Generate candidate positions for the current garden state."""
        if len(garden.plants) == 0:
            # First plant: use grid
            return generate_grid_candidates(
                garden,
                self.config['geometry']['grid_samples']
            )
        else:
            # Subsequent plants: use geometric candidates
            representative_variety = self.all_varieties[0]
            return generate_geometric_candidates(
                garden,
                representative_variety,
                self.config['geometry']['angle_samples'],
                self.config['geometry']['max_anchor_pairs']
            )
    
    def _prune_candidates(self, garden: Garden, candidates: List[Position], 
                          varieties: List[PlantVariety]) -> List[Position]:
        """Prune candidates using geometric heuristic."""
        max_candidates = self.config['geometry']['max_candidates']
        
        if len(varieties) == 0:
            return []
        
        representative_variety = varieties[0]
        
        # Score each candidate
        scored_candidates = []
        for pos in candidates:
            score = geometric_heuristic(
                pos,
                garden,
                representative_variety,
                self.config['heuristic']['lambda_interact'],
                self.config['heuristic']['lambda_gap']
            )
            scored_candidates.append((score, pos))
        
        # Sort by score (descending) and keep top K
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [pos for _, pos in scored_candidates[:max_candidates]]
    
    def _get_nutrient_priorities(self, garden: Garden, varieties: List[PlantVariety]) -> List[PlantVariety]:
        """
        Prioritize varieties based on global nutrient production balance.
        """
        if len(garden.plants) == 0:
            return varieties.copy()
        
        # Calculate total nutrient production in current garden
        total_R = 0.0
        total_G = 0.0
        total_B = 0.0
        
        for plant in garden.plants:
            coeffs = plant.variety.nutrient_coefficients
            total_R += coeffs.get(Micronutrient.R, 0.0)
            total_G += coeffs.get(Micronutrient.G, 0.0)
            total_B += coeffs.get(Micronutrient.B, 0.0)
        
        # Find which nutrient is lowest (most needed)
        nutrient_totals = {
            Micronutrient.R: total_R,
            Micronutrient.G: total_G,
            Micronutrient.B: total_B
        }
        
        # Score each variety based on how much it produces the lowest nutrient
        # Map species to micronutrient
        from core.plants.species import Species
        species_to_nutrient = {
            Species.RHODODENDRON: Micronutrient.R,
            Species.GERANIUM: Micronutrient.G,
            Species.BEGONIA: Micronutrient.B
        }
        
        def priority_score(variety):
            variety_nutrient = species_to_nutrient[variety.species]
            variety_production = variety.nutrient_coefficients.get(variety_nutrient, 0.0)
            
            # Higher score if this variety produces the nutrient that is currently lowest
            current_production = nutrient_totals[variety_nutrient]
            
            # Invert: lower current production = higher priority
            return -current_production + variety_production
        
        sorted_varieties = sorted(
            varieties,
            key=priority_score,
            reverse=True
        )
        
        return sorted_varieties
    
    def _expand_state(self, state: Dict, variety: PlantVariety, position: Position) -> Optional[Dict]:
        """
        Expand a beam state by placing a variety at a position.
        Returns new state or None if placement fails.
        """
        # Deep copy the garden
        new_garden = copy.deepcopy(state['garden'])
        
        # Try to place the plant
        try:
            result = new_garden.add_plant(variety, position)
            if result is None:
                return None
        except Exception as e:
            if self.config['debug']['verbose']:
                print(f"    Placement failed: {e}")
            return None
        
        # Remove this variety from the remaining list
        new_varieties = state['varieties'].copy()
        # Find and remove the first occurrence of this variety
        for i, v in enumerate(new_varieties):
            if id(v) == id(variety):
                new_varieties.pop(i)
                break
        
        # Evaluate this placement
        T_placement = self.config['simulation'].get('T_placement', 20)
        w_short = self.config['simulation']['w_short']
        w_long = self.config['simulation']['w_long']
        
        new_score = simulate_and_score(new_garden, T_placement, w_short, w_long)
        
        # Create new state
        new_state = {
            'garden': new_garden,
            'varieties': new_varieties,
            'score': new_score,
            'history': state['history'] + [(variety.name, position)]
        }
        
        return new_state

