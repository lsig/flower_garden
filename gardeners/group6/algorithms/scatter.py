"""Initial plant positioning."""

import random

# NOTE: Originally used numpy for array operations. Original implementation used:
# import numpy as np
from core.plants.plant_variety import PlantVariety


def scatter_seeds_randomly(
    varieties: list[PlantVariety], W: float = 16.0, H: float = 10.0, target_count: int = None
) -> tuple[list[tuple[float, float]], list[int], list[list[float]]]:
    """Scatter plant seeds randomly across the garden.

    Args:
        varieties: List of available plant varieties
        W: Garden width
        H: Garden height
        target_count: Number of plants to scatter (can be more than len(varieties))
                     If None, uses len(varieties)
    """
    # NUMPY: Originally returned (np.ndarray, list[int], np.ndarray)
    # where np.ndarray had shape (N, 2) for coordinates and (N, 3) for inventories
    num_varieties = len(varieties)
    N = target_count if target_count is not None else num_varieties

    # Random positions with margin from edges to prevent boundary clustering
    margin = 1.0
    # TODO: we use random here, so we might need to ensure we are using the right random seed.
    # NUMPY: Originally used np.random.uniform([margin, margin], [W - margin, H - margin], size=(N, 2))
    X = [(random.uniform(margin, W - margin), random.uniform(margin, H - margin)) for _ in range(N)]

    # Labels: cycle through varieties if we need more plants than varieties
    # NUMPY: Originally used np.arange(num_varieties) and np.random.choice()
    labels = list(range(num_varieties))
    if num_varieties < N:
        extra = [random.randint(0, num_varieties - 1) for _ in range(N - num_varieties)]
        labels.extend(extra)
    random.shuffle(labels)

    # Initialize inventories to half-full (5 * radius for each nutrient)
    # NUMPY: Originally used np.zeros((N, 3)) and direct assignment inv[i] = [...]
    inv = []
    for i in range(N):
        variety = varieties[labels[i]]
        half_capacity = 5.0 * variety.radius
        inv.append([half_capacity, half_capacity, half_capacity])

    return X, labels, inv

