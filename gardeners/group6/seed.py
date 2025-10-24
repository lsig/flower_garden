"""Seed generation utilities for initial plant positions."""

import random
from typing import Tuple, List


def get_random_point(min_x: float, max_x: float, min_y: float, max_y: float) -> Tuple[float, float]:
    """Generate a random point within a rectangular region."""
    x = random.uniform(min_x, max_x)
    y = random.uniform(min_y, max_y)
    return (x, y)


def get_random_points(n: int, width: float = 16.0, height: float = 10.0) -> List[Tuple[float, float]]:
    """Generate n random points in the garden."""
    return [get_random_point(0, width, 0, height) for _ in range(n)]



