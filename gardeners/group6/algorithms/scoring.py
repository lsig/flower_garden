"""Garden layout quality evaluation."""

import math

# NOTE: Originally used numpy for array operations. Original implementation used:
# import numpy as np
from core.plants.plant_variety import PlantVariety


def measure_garden_quality(
    X: list[tuple[float, float]],
    varieties: list[PlantVariety],
    labels: list[int],
    lambda_weight: float = 1.5,
) -> float:
    """Measure the quality of a garden layout."""
    # NUMPY: Originally used np.ndarray for X parameter
    N = len(X)
    cross_species_edges = 0
    # NUMPY: Originally used np.zeros(N, dtype=int)
    degrees = [0] * N

    same_species_penalty = 0


    for i in range(N):
        for j in range(i + 1, N):
            species_i = varieties[labels[i]].species
            species_j = varieties[labels[j]].species
            r_i = varieties[labels[i]].radius
            r_j = varieties[labels[j]].radius

            # NUMPY: Originally used delta = X[i] - X[j] and np.linalg.norm(delta)
            delta_x = X[i][0] - X[j][0]
            delta_y = X[i][1] - X[j][1]
            dist = math.sqrt(delta_x * delta_x + delta_y * delta_y)

            interaction_range = r_i + r_j
            same_species_range_sq = (interaction_range * 1.2) ** 2

            # Cross-species within interaction range
            if species_i != species_j and dist < r_i + r_j:
                cross_species_edges += 1
                degrees[i] += 1
                degrees[j] += 1

            # Penalty if plants of the same species are too close to each other
            if species_i == species_j and dist < (r_i + r_j):
                penalty = 1 - (dist / same_species_range_sq)
                same_species_penalty -= penalty

    # Count nodes with degree >= 2
    # NUMPY: Originally used np.sum(degrees >= 2)
    nodes_with_degree_2_plus = sum(1 for d in degrees if d >= 2)

    score = cross_species_edges + lambda_weight * nodes_with_degree_2_plus + same_species_penalty 
    return score
