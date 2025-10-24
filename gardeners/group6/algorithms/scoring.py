"""Garden layout quality evaluation."""

import numpy as np
from typing import List
from core.plants.plant_variety import PlantVariety


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
