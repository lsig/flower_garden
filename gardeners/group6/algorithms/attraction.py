"""Beneficial interaction creation using attractive forces."""

import math

# NOTE: Originally used numpy for array operations. Original implementation used:
# import numpy as np
from core.plants.plant_variety import PlantVariety

# Optional tqdm import for progress bars
try:
    from tqdm import tqdm
except ImportError:

    def tqdm(iterable, desc=None, leave=None):
        return iterable


def create_beneficial_interactions(
    X: list[tuple[float, float]],
    varieties: list[PlantVariety],
    labels: list[int],
    inv: list[list[float]],
    iters: int = 200,
    band_delta: float = 0.25,
    degree_cap: int = 4,
    step_size: float = 0.05,
    keep_feasible: bool = True,
) -> list[tuple[float, float]]:
    """Create beneficial interactions by pulling cross-species plants together."""
    # NUMPY: Originally used np.ndarray for X and inv parameters
    N = len(X)

    for _iteration in tqdm(range(iters), desc='Creating beneficial interactions', leave=False):
        # NUMPY: Originally used np.zeros_like(X) for forces array
        forces = [(0.0, 0.0) for _ in range(N)]

        # Count cross-species neighbors for degree damping
        # NUMPY: Originally used np.zeros(N, dtype=int)
        cross_species_degrees = [0] * N

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
                        # NUMPY: Originally used direction = delta / dist
                        direction_x = delta_x / dist
                        direction_y = delta_y / dist
                        displacement = dist - target_dist

                        # Dampen if high degree
                        damping_i = 1.0 if cross_species_degrees[i] < degree_cap else 0.3
                        damping_j = 1.0 if cross_species_degrees[j] < degree_cap else 0.3
                        damping = min(damping_i, damping_j)

                        # Pull together if too far, push apart if too close
                        force_magnitude = -displacement * 0.3 * damping

                        # NUMPY: Originally used forces[i] += direction * force_magnitude
                        forces[i] = (
                            forces[i][0] + direction_x * force_magnitude,
                            forces[i][1] + direction_y * force_magnitude,
                        )
                        forces[j] = (
                            forces[j][0] - direction_x * force_magnitude,
                            forces[j][1] - direction_y * force_magnitude,
                        )
                else:
                    interaction_radius = r_i + r_j
                    if dist > 1e-6:
                        # NUMPY: Originally used direction = delta / dist
                        direction_x = delta_x / dist
                        direction_y = delta_y / dist

                        desired_spacing = interaction_radius * 1.5
                        overlap = max(0.0, desired_spacing - dist)

                        force_magnitude = overlap * 0.6

                        # NUMPY: Originally used forces[i] += direction * force_magnitude
                        forces[i] = (
                            forces[i][0] - direction_x * force_magnitude,
                            forces[i][1] - direction_y * force_magnitude,
                        )
                        forces[j] = (
                            forces[j][0] + direction_x * force_magnitude,
                            forces[j][1] + direction_y * force_magnitude,
                        )

                # Feasibility: repulsive force for overlaps
                if keep_feasible:
                    min_dist = max(r_i, r_j)
                    if dist < min_dist and dist > 1e-6:
                        # NUMPY: Originally used direction = delta / dist
                        direction_x = delta_x / dist
                        direction_y = delta_y / dist
                        violation = min_dist - dist
                        force_magnitude = violation * 0.5

                        # NUMPY: Originally used forces[i] += direction * force_magnitude
                        forces[i] = (
                            forces[i][0] + direction_x * force_magnitude,
                            forces[i][1] + direction_y * force_magnitude,
                        )
                        forces[j] = (
                            forces[j][0] - direction_x * force_magnitude,
                            forces[j][1] - direction_y * force_magnitude,
                        )

        # Apply forces
        # NUMPY: Originally used X += forces * step_size
        for i in range(N):
            X[i] = (X[i][0] + forces[i][0] * step_size, X[i][1] + forces[i][1] * step_size)

        # Keep within garden bounds with margin
        margin = 0.5
        W, H = 16.0, 10.0
        # NUMPY: Originally used np.clip(X[:, 0], margin, W - margin)
        for i in range(N):
            x, y = X[i]
            X[i] = (max(margin, min(W - margin, x)), max(margin, min(H - margin, y)))

    return X
