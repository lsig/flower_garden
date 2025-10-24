"""Force-directed layout algorithms for plant placement."""

import random
import numpy as np
from typing import List, Tuple
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species


def scatter_seeds(varieties: List[PlantVariety], W: float = 16.0, H: float = 10.0) -> Tuple[np.ndarray, List[int], np.ndarray]:
    """Scatter plant seeds randomly across the garden."""
    N = len(varieties)
    
    # Random positions in garden
    X = np.zeros((N, 2))
    X[:, 0] = np.random.uniform(0, W, N)
    X[:, 1] = np.random.uniform(0, H, N)
    
    # Labels are just indices 0..N-1
    labels = list(range(N))
    
    # Initialize inventories to half-full (5 * radius for each nutrient)
    inv = np.zeros((N, 3))
    for i, variety in enumerate(varieties):
        half_capacity = 5.0 * variety.radius
        inv[i] = [half_capacity, half_capacity, half_capacity]
    
    return X, labels, inv


def separate_overlapping_plants(
    X: np.ndarray,
    varieties: List[PlantVariety],
    labels: List[int],
    iters: int = 300,
    step_size: float = 0.1,
    jitter_interval: int = 20,
    jitter_amount: float = 0.01
) -> np.ndarray:
    """Separate overlapping plants using repulsive forces."""
    N = len(X)
    
    for iteration in range(iters):
        forces = np.zeros_like(X)
        
        # Check all pairs for overlaps
        for i in range(N):
            for j in range(i + 1, N):
                # Get radii
                r_i = varieties[labels[i]].radius
                r_j = varieties[labels[j]].radius
                min_dist = max(r_i, r_j)
                
                # Calculate distance
                delta = X[i] - X[j]
                dist = np.linalg.norm(delta)
                
                # If overlapping, push apart
                if dist < min_dist and dist > 1e-6:
                    # Normalize direction
                    direction = delta / dist
                    # Repulsive force proportional to violation
                    violation = min_dist - dist
                    force_magnitude = violation * 0.5
                    
                    forces[i] += direction * force_magnitude
                    forces[j] -= direction * force_magnitude
                elif dist <= 1e-6:
                    # Handle exact overlaps with random push
                    random_dir = np.random.randn(2)
                    random_dir /= np.linalg.norm(random_dir)
                    forces[i] += random_dir * min_dist * 0.5
                    forces[j] -= random_dir * min_dist * 0.5
        
        # Apply forces
        X += forces * step_size
        
        # Add jitter periodically to escape local minima
        if (iteration + 1) % jitter_interval == 0:
            X += np.random.randn(*X.shape) * jitter_amount
    
    return X


def create_beneficial_interactions(
    X: np.ndarray,
    varieties: List[PlantVariety],
    labels: List[int],
    inv: np.ndarray,
    iters: int = 200,
    band_delta: float = 0.25,
    degree_cap: int = 4,
    step_size: float = 0.05,
    keep_feasible: bool = True
) -> np.ndarray:
    """Create beneficial interactions by pulling cross-species plants together."""
    N = len(X)
    
    for iteration in range(iters):
        forces = np.zeros_like(X)
        
        # Count cross-species neighbors for degree damping
        cross_species_degrees = np.zeros(N, dtype=int)
        
        for i in range(N):
            for j in range(i + 1, N):
                species_i = varieties[labels[i]].species
                species_j = varieties[labels[j]].species
                r_i = varieties[labels[i]].radius
                r_j = varieties[labels[j]].radius
                
                delta = X[i] - X[j]
                dist = np.linalg.norm(delta)
                
                # Cross-species interaction
                if species_i != species_j:
                    interaction_radius = r_i + r_j
                    target_dist = interaction_radius - band_delta
                    
                    # Count as neighbor if within interaction range
                    if dist < interaction_radius:
                        cross_species_degrees[i] += 1
                        cross_species_degrees[j] += 1
                    
                    # Attractive force toward target distance
                    if dist > 1e-6:
                        direction = delta / dist
                        displacement = dist - target_dist
                        
                        # Dampen if high degree
                        damping_i = 1.0 if cross_species_degrees[i] < degree_cap else 0.3
                        damping_j = 1.0 if cross_species_degrees[j] < degree_cap else 0.3
                        damping = min(damping_i, damping_j)
                        
                        # Pull together if too far, push apart if too close
                        force_magnitude = -displacement * 0.3 * damping
                        
                        forces[i] += direction * force_magnitude
                        forces[j] -= direction * force_magnitude
                
                # Feasibility: repulsive force for overlaps
                if keep_feasible:
                    min_dist = max(r_i, r_j)
                    if dist < min_dist and dist > 1e-6:
                        direction = delta / dist
                        violation = min_dist - dist
                        force_magnitude = violation * 0.5
                        
                        forces[i] += direction * force_magnitude
                        forces[j] -= direction * force_magnitude
        
        # Apply forces
        X += forces * step_size
    
    return X


def measure_garden_quality(
    X: np.ndarray,
    varieties: List[PlantVariety],
    labels: List[int],
    lambda_weight: float = 1.5
) -> float:
    """Measure the quality of a garden layout."""
    N = len(X)
    cross_species_edges = 0
    degrees = np.zeros(N, dtype=int)
    
    for i in range(N):
        for j in range(i + 1, N):
            species_i = varieties[labels[i]].species
            species_j = varieties[labels[j]].species
            r_i = varieties[labels[i]].radius
            r_j = varieties[labels[j]].radius
            
            delta = X[i] - X[j]
            dist = np.linalg.norm(delta)
            
            # Cross-species within interaction range
            if species_i != species_j and dist < r_i + r_j:
                cross_species_edges += 1
                degrees[i] += 1
                degrees[j] += 1
    
    # Count nodes with degree >= 2
    nodes_with_degree_2_plus = np.sum(degrees >= 2)
    
    score = cross_species_edges + lambda_weight * nodes_with_degree_2_plus
    return score

