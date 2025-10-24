"""
Seed generation utilities for Group 6 Gardener.

This module provides functions for generating initial plant positions.
Currently implements simple uniform random sampling.

Future extensions could include:
- Mixed-radius Poisson-disk sampling
- Stratified sampling (grid-based with jitter)
- Species-aware initialization (alternate species in spatial regions)
"""

import random
from typing import Tuple, List


def get_random_point(min_x: float, max_x: float, min_y: float, max_y: float) -> Tuple[float, float]:
    """
    Generate a random point within a rectangular region.
    
    Args:
        min_x: Minimum x coordinate
        max_x: Maximum x coordinate
        min_y: Minimum y coordinate
        max_y: Maximum y coordinate
    
    Returns:
        (x, y) tuple with random coordinates
    """
    x = random.uniform(min_x, max_x)
    y = random.uniform(min_y, max_y)
    return (x, y)


def get_random_points(n: int, width: float = 16.0, height: float = 10.0) -> List[Tuple[float, float]]:
    """
    Generate n random points in the garden.
    
    Args:
        n: Number of points to generate
        width: Garden width (meters)
        height: Garden height (meters)
    
    Returns:
        List of (x, y) tuples
    """
    return [get_random_point(0, width, 0, height) for _ in range(n)]


# Notes on Poisson Disk Sampling (future extension):
#
# Regular disk sampling algorithm:
# 1. Generate a random point on the grid
# 2. Define a radius r and 2r radius disk around the point
# 3. Randomly sample a point in the 2r disk (annulus between r and 2r)
# 4. Check if new point is at least r away from all existing points
# 5. If valid, add to active list; otherwise reject
# 6. Repeat until no more points can be placed
#
# For mixed-radius (our case):
# - Each plant has its own radius r_i
# - Minimum distance between plants i,j is max(r_i, r_j)
# - Need to track per-plant radii in spatial data structure
#
# Spatial acceleration:
# - Subdivide bounding box into grid with cell size = min_radius / sqrt(2)
# - Only check plants in neighboring cells (9 cells in 2D)
# - Reduces collision checks from O(N) to O(1) per candidate
#
# Grid type considerations:
# - Square grid: Simple, standard
# - Hex grid: Better packing efficiency (~15% more points)
# - For our problem: Square grid is sufficient, hex adds complexity
#
# Implementation priority: Low (random works well enough for MVP)

