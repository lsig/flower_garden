"""Custom simulation logic for evaluating plant layouts."""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.micronutrients import Micronutrient


@dataclass
class SimulationResult:
    """Results from a simulation run."""
    final_growth: float
    total_turns: int
    growth_history: List[float]
    stagnation_stopped: bool
    metric_value: float


class PlantState:
    """Tracks state of a single plant during simulation."""
    
    def __init__(self, variety: PlantVariety, position: Tuple[float, float], initial_inv: np.ndarray):
        self.variety = variety
        self.position = np.array(position)
        self.reservoir_capacity = 10.0 * variety.radius
        self.max_size = 100.0 * (variety.radius ** 2)
        
        # State variables
        self.size = 0.0
        self.inventory = initial_inv.copy()  # [R, G, B]
    
    def get_produced_nutrient_index(self) -> int:
        """Get index (0=R, 1=G, 2=B) of nutrient this plant produces."""
        if self.variety.species == Species.RHODODENDRON:
            return 0  # R
        elif self.variety.species == Species.GERANIUM:
            return 1  # G
        else:  # BEGONIA
            return 2  # B
    
    def can_produce(self) -> bool:
        """Check if production would make any nutrient negative."""
        coeffs = self.variety.nutrient_coefficients
        test_inv = self.inventory.copy()
        test_inv[0] += coeffs[Micronutrient.R]
        test_inv[1] += coeffs[Micronutrient.G]
        test_inv[2] += coeffs[Micronutrient.B]
        return np.all(test_inv >= 0)
    
    def produce(self):
        """Produce micronutrients according to variety coefficients."""
        if not self.can_produce():
            return
        
        coeffs = self.variety.nutrient_coefficients
        self.inventory[0] += coeffs[Micronutrient.R]
        self.inventory[1] += coeffs[Micronutrient.G]
        self.inventory[2] += coeffs[Micronutrient.B]
        
        # Cap at reservoir capacity
        self.inventory = np.minimum(self.inventory, self.reservoir_capacity)
    
    def can_grow(self) -> bool:
        """Check if plant has enough nutrients to grow and isn't at max size."""
        min_needed = 2.0 * self.variety.radius
        return np.all(self.inventory >= min_needed) and self.size < self.max_size
    
    def grow(self) -> float:
        """Consume nutrients and grow. Returns growth amount."""
        if not self.can_grow():
            return 0.0
        
        # Consume nutrients
        consumption = self.variety.radius
        self.inventory -= consumption
        
        # Grow
        self.size += self.variety.radius
        return self.variety.radius
    
    def offer_amount(self) -> float:
        """Calculate offer amount (1/4 of produced nutrient inventory)."""
        produced_idx = self.get_produced_nutrient_index()
        return self.inventory[produced_idx] / 4.0


def simulate(
    X: np.ndarray,
    varieties: List[PlantVariety],
    labels: List[int],
    inv: np.ndarray,
    max_turns: int = 300,
    early_stop: int = 10,
    metric: str = "total_growth"
) -> SimulationResult:
    """
    Run full simulation with day/evening/night cycles.
    
    Args:
        X: N×2 array of positions
        varieties: List of all plant varieties
        labels: List mapping plant index to variety index
        inv: N×3 array of initial inventories
        max_turns: Maximum simulation turns
        early_stop: Stop if no growth for this many consecutive turns
        metric: Metric to optimize ("total_growth", "fastest_to_g", etc.)
    
    Returns:
        SimulationResult with final metrics
    """
    N = len(X)
    
    # Initialize plant states
    plants = []
    for i in range(N):
        plant = PlantState(
            variety=varieties[labels[i]],
            position=(X[i, 0], X[i, 1]),
            initial_inv=inv[i]
        )
        plants.append(plant)
    
    # Build interaction graph (which plants can exchange)
    interactions = _build_interaction_graph(plants)
    
    # Simulation loop
    growth_history = []
    stagnant_count = 0
    
    for turn in range(max_turns):
        # DAYTIME: Production
        for plant in plants:
            plant.produce()
        
        # EVENING: Exchange
        _execute_exchanges(plants, interactions)
        
        # OVERNIGHT: Growth
        turn_growth = 0.0
        for plant in plants:
            turn_growth += plant.grow()
        
        # Track total growth
        total_growth = sum(plant.size for plant in plants)
        growth_history.append(total_growth)
        
        # Early stopping check
        if turn_growth < 1e-6:
            stagnant_count += 1
            if stagnant_count >= early_stop:
                break
        else:
            stagnant_count = 0
    
    # Calculate final metrics
    final_growth = sum(plant.size for plant in plants)
    metric_value = _calculate_metric(plants, growth_history, metric)
    
    return SimulationResult(
        final_growth=final_growth,
        total_turns=len(growth_history),
        growth_history=growth_history,
        stagnation_stopped=(stagnant_count >= early_stop),
        metric_value=metric_value
    )


def _build_interaction_graph(plants: List[PlantState]) -> List[Tuple[int, int]]:
    """
    Build list of plant pairs that can interact (different species, overlapping roots).
    
    Returns:
        List of (i, j) tuples where i < j
    """
    interactions = []
    N = len(plants)
    
    for i in range(N):
        for j in range(i + 1, N):
            # Must be different species
            if plants[i].variety.species == plants[j].variety.species:
                continue
            
            # Must have overlapping root systems
            dist = np.linalg.norm(plants[i].position - plants[j].position)
            interaction_dist = plants[i].variety.radius + plants[j].variety.radius
            
            if dist < interaction_dist:
                interactions.append((i, j))
    
    return interactions


def _execute_exchanges(plants: List[PlantState], interactions: List[Tuple[int, int]]):
    """
    Execute nutrient exchanges between interacting plants.
    
    Exchange protocol:
    1. Each plant offers 1/4 of its produced nutrient, split among partners
    2. Exchange amount = min(offer_i, offer_j)
    3. Only exchange if both plants have surplus (giving > receiving)
    4. Apply all exchanges synchronously
    """
    # Calculate offers per partner for each plant
    partner_counts = {}
    for i, j in interactions:
        partner_counts[i] = partner_counts.get(i, 0) + 1
        partner_counts[j] = partner_counts.get(j, 0) + 1
    
    offers_per_partner = {}
    for plant_idx, count in partner_counts.items():
        total_offer = plants[plant_idx].offer_amount()
        offers_per_partner[plant_idx] = total_offer / count if count > 0 else 0.0
    
    # Determine which exchanges should happen and calculate amounts
    exchanges_to_apply = []
    
    for i, j in interactions:
        plant_i = plants[i]
        plant_j = plants[j]
        
        produced_i = plant_i.get_produced_nutrient_index()
        produced_j = plant_j.get_produced_nutrient_index()
        
        # Check if both have surplus (giving > receiving)
        has_surplus_i = plant_i.inventory[produced_i] > plant_i.inventory[produced_j]
        has_surplus_j = plant_j.inventory[produced_j] > plant_j.inventory[produced_i]
        
        if not (has_surplus_i and has_surplus_j):
            continue
        
        # Calculate exchange amount
        offer_i = offers_per_partner.get(i, 0.0)
        offer_j = offers_per_partner.get(j, 0.0)
        exchange_amount = min(offer_i, offer_j)
        
        if exchange_amount > 0:
            exchanges_to_apply.append((i, j, produced_i, produced_j, exchange_amount))
    
    # Apply all exchanges synchronously
    for i, j, nutrient_i, nutrient_j, amount in exchanges_to_apply:
        # Plant i gives nutrient_i, receives nutrient_j
        plants[i].inventory[nutrient_i] -= amount
        plants[i].inventory[nutrient_j] = min(
            plants[i].inventory[nutrient_j] + amount,
            plants[i].reservoir_capacity
        )
        
        # Plant j gives nutrient_j, receives nutrient_i
        plants[j].inventory[nutrient_j] -= amount
        plants[j].inventory[nutrient_i] = min(
            plants[j].inventory[nutrient_i] + amount,
            plants[j].reservoir_capacity
        )


def _calculate_metric(plants: List[PlantState], growth_history: List[float], metric: str) -> float:
    """Calculate the specified metric value."""
    if metric == "total_growth":
        return growth_history[-1] if growth_history else 0.0
    
    elif metric == "fastest_to_g":
        # Return turn number when reached target G (placeholder: use 50% of theoretical max)
        target = sum(plant.max_size for plant in plants) * 0.5
        for turn, growth in enumerate(growth_history):
            if growth >= target:
                return float(turn)
        return float(len(growth_history))
    
    elif metric == "biggest_in_t":
        # Return growth at intermediate time T (e.g., T=100)
        T = min(100, len(growth_history) - 1)
        return growth_history[T] if T >= 0 else 0.0
    
    elif metric == "no_plant_left_behind":
        # Return turn when all plants reached 50% of their capacity
        for turn in range(len(growth_history)):
            all_half = all(plant.size >= 0.5 * plant.max_size for plant in plants)
            if all_half:
                return float(turn)
        return float(len(growth_history))
    
    else:
        # Default to total growth
        return growth_history[-1] if growth_history else 0.0

