"""Initial plant positioning."""

import numpy as np
from typing import List, Tuple
from core.plants.plant_variety import PlantVariety


def scatter_seeds_randomly(varieties: List[PlantVariety], W: float = 16.0, H: float = 10.0, target_count: int = None) -> Tuple[np.ndarray, List[int], np.ndarray]:
    """Scatter plant seeds randomly across the garden.
    
    Args:
        varieties: List of available plant varieties
        W: Garden width
        H: Garden height
        target_count: Number of plants to scatter (can be more than len(varieties))
                     If None, uses len(varieties)
    """
    num_varieties = len(varieties)
    N = target_count if target_count is not None else num_varieties
    
    # Random positions with margin from edges to prevent boundary clustering
    margin = 1.0
    X = np.zeros((N, 2))
    # TODO: we use random here, so we might need to ensure we are using the right random seed.
    X[:, 0] = np.random.uniform(margin, W - margin, N)
    X[:, 1] = np.random.uniform(margin, H - margin, N)
    
    # Labels: cycle through varieties if we need more plants than varieties
    labels = [i % num_varieties for i in range(N)]
    
    # Initialize inventories to half-full (5 * radius for each nutrient)
    inv = np.zeros((N, 3))
    for i in range(N):
        variety = varieties[labels[i]]
        half_capacity = 5.0 * variety.radius
        inv[i] = [half_capacity, half_capacity, half_capacity]
    
    return X, labels, inv
