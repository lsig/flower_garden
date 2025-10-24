"""Beneficial interaction creation using attractive forces."""

import numpy as np
from typing import List
from core.plants.plant_variety import PlantVariety

# Optional tqdm import for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=None, leave=None):
        return iterable


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
    
    for iteration in tqdm(range(iters), desc="Creating beneficial interactions", leave=False):
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
        
        # Keep within garden bounds with margin
        margin = 0.5
        W, H = 16.0, 10.0
        X[:, 0] = np.clip(X[:, 0], margin, W - margin)
        X[:, 1] = np.clip(X[:, 1], margin, H - margin)
    
    return X
