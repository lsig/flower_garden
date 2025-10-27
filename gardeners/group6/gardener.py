"""Force-directed layout algorithm for optimal plant placement."""

import math
import random
# NOTE: Originally used numpy for array operations, but replaced with standard Python
# to avoid external dependencies. Original implementation used:
# import numpy as np

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position

# Optional tqdm import for progress bars
try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    # Fallback: tqdm is just a pass-through function
    def tqdm(iterable, desc=None, leave=None):
        return iterable


from gardeners.group6.algorithms import (
    create_beneficial_interactions,
    measure_garden_quality,
    scatter_seeds_randomly,
    separate_overlapping_plants,
)


class Gardener6(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

        # Dynamic scaling based on nursery size
        num_plants = len(varieties)

        # Limit to 50 plants for very large configs, but ensure species diversity
        if num_plants > 50:
            # Shuffle to get representative sample from all species
            random.shuffle(varieties)
            self.varieties = varieties[:50]
            num_plants = 50

        # Scale parameters inversely with problem size
        scale_factor = max(1, num_plants // 10)  # 1 for ≤10, 2 for ≤20, 5 for ≤50
        self.num_seeds = max(3, 18 // scale_factor)
        self.feasible_iters = max(40, 300 // scale_factor)
        self.nutrient_iters = max(75, 420 // scale_factor)

        # Adjust force parameters to prevent over-clustering
        self.band_delta = 0.25
        self.degree_cap = 5
        self.top_k_simulate = 1
        self.step_size_feasible = 0.18  # Stronger separation forces
        self.step_size_nutrient = 0.0002  # Weaker attraction forces

    def cultivate_garden(self) -> None:
        """Place plants optimally using force-directed layout."""
        if not self.varieties:
            return

        best_score = -float('inf')
        best_layout = None
        best_labels = None

        # Calculate how many plants to try placing
        # Aim for ~2x the variety count to fill empty spaces
        target_plants = min(len(self.varieties) * 8, 320)

        # Multi-start: try multiple random seeds
        for _seed_idx in tqdm(range(self.num_seeds), desc='Multi-start optimization', leave=True):
            # Step 1: Scatter MORE seeds than varieties to fill space
            X, labels, inv = scatter_seeds_randomly(
                self.varieties,
                W=self.garden.width,
                H=self.garden.height,
                target_count=target_plants,
            )

            # Step 2: Create beneficial interactions FIRST
            X = create_beneficial_interactions(
                X,
                self.varieties,
                labels,
                inv,
                iters=self.nutrient_iters,
                band_delta=self.band_delta,
                degree_cap=self.degree_cap,
                step_size=self.step_size_nutrient,
                keep_feasible=False,  # Don't enforce separation yet
            )

            # Step 3: Separate ONLY plants that violate hard constraints
            X = separate_overlapping_plants(
                X,
                self.varieties,
                labels,
                iters=self.feasible_iters // 2,  # Fewer iterations
                step_size=self.step_size_feasible * 0.5,  # Gentler separation
            )

            # Step 4: Measure garden quality
            score = measure_garden_quality(X, self.varieties, labels)

            # Keep best
            if score > best_score:
                best_score = score
                # NUMPY: Originally used X.copy() for numpy array copying
                best_layout = [pos for pos in X]  # Copy list of positions
                best_labels = labels.copy()

        # Place the best layout in the garden
        if best_layout is not None:
            self._place_plants(best_layout, best_labels)

    def _place_plants(self, X: list[tuple[float, float]], labels: list[int]) -> None:
        """Place plants from layout into the garden."""
        # NUMPY: Originally used np.ndarray with shape (N, 2) for coordinates
        # Access was X[i, 0] and X[i, 1] instead of X[i][0] and X[i][1]
        for i, label in enumerate(labels):
            variety = self.varieties[label]
            position = Position(x=X[i][0], y=X[i][1])

            # Attempt to place plant
            self.garden.add_plant(variety, position)
