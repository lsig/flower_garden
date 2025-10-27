"""Plant separation using repulsive forces."""

import math
import random

# NOTE: Originally used numpy for array operations. Original implementation used:
# import numpy as np
from core.plants.plant_variety import PlantVariety

# Optional tqdm import for progress bars
try:
    from tqdm import tqdm
except ImportError:

    def tqdm(iterable, desc=None, leave=None):
        return iterable


def separate_overlapping_plants(
    X: list[tuple[float, float]],
    varieties: list[PlantVariety],
    labels: list[int],
    iters: int = 300,
    step_size: float = 0.1,
    jitter_interval: int = 20,
    jitter_amount: float = 0.01,
) -> list[tuple[float, float]]:
    """Separate overlapping plants using repulsive forces."""
    # NUMPY: Originally used np.ndarray for X parameter
    N = len(X)

    for iteration in tqdm(range(iters), desc='Separating overlapping plants', leave=False):
        # NUMPY: Originally used np.zeros_like(X) for forces array
        forces = [(0.0, 0.0) for _ in range(N)]

        # Check all pairs for overlaps
        for i in range(N):
            for j in range(i + 1, N):
                # Get radii
                r_i = varieties[labels[i]].radius
                r_j = varieties[labels[j]].radius
                min_dist = max(r_i, r_j)

                # Calculate distance
                # NUMPY: Originally used delta = X[i] - X[j] and np.linalg.norm(delta)
                delta_x = X[i][0] - X[j][0]
                delta_y = X[i][1] - X[j][1]
                dist = math.sqrt(delta_x * delta_x + delta_y * delta_y)

                # If overlapping, push apart
                if dist < min_dist and dist > 1e-6:
                    # Normalize direction
                    # NUMPY: Originally used direction = delta / dist
                    direction_x = delta_x / dist
                    direction_y = delta_y / dist
                    # Repulsive force proportional to violation
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
                elif dist <= 1e-6:
                    # Handle exact overlaps with random push
                    # TODO: we use random here, so we might need to ensure we are using the right random seed.
                    # NUMPY: Originally used np.random.randn(2) and np.linalg.norm(random_dir)
                    random_dir_x = random.gauss(0, 1)
                    random_dir_y = random.gauss(0, 1)
                    norm = math.sqrt(random_dir_x * random_dir_x + random_dir_y * random_dir_y)
                    random_dir_x /= norm
                    random_dir_y /= norm
                    # NUMPY: Originally used forces[i] += random_dir * min_dist * 0.5
                    forces[i] = (
                        forces[i][0] + random_dir_x * min_dist * 0.5,
                        forces[i][1] + random_dir_y * min_dist * 0.5,
                    )
                    forces[j] = (
                        forces[j][0] - random_dir_x * min_dist * 0.5,
                        forces[j][1] - random_dir_y * min_dist * 0.5,
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

        # Add jitter periodically to escape local minima
        if (iteration + 1) % jitter_interval == 0:
            # TODO: we use random here, so we might need to ensure we are using the right random seed.
            # NUMPY: Originally used X += np.random.randn(*X.shape) * jitter_amount
            for i in range(N):
                jitter_x = random.gauss(0, jitter_amount)
                jitter_y = random.gauss(0, jitter_amount)
                X[i] = (X[i][0] + jitter_x, X[i][1] + jitter_y)

    return X
