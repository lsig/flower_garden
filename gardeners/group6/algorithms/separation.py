"""Plant separation using repulsive forces."""

import numpy as np
from typing import List
from core.plants.plant_variety import PlantVariety

# Optional tqdm import for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=None, leave=None):
        return iterable


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
    
    for iteration in tqdm(range(iters), desc="Separating overlapping plants", leave=False):
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
                    # TODO: we use random here, so we might need to ensure we are using the right random seed.
                    random_dir = np.random.randn(2)
                    random_dir /= np.linalg.norm(random_dir)
                    forces[i] += random_dir * min_dist * 0.5
                    forces[j] -= random_dir * min_dist * 0.5
        
        # Apply forces
        X += forces * step_size
        
        # Keep within garden bounds with margin
        margin = 0.5
        W, H = 16.0, 10.0
        X[:, 0] = np.clip(X[:, 0], margin, W - margin)
        X[:, 1] = np.clip(X[:, 1], margin, H - margin)
        
        # Add jitter periodically to escape local minima
        if (iteration + 1) % jitter_interval == 0:
            # TODO: we use random here, so we might need to ensure we are using the right random seed.
            X += np.random.randn(*X.shape) * jitter_amount
    
    return X
