"""Utility functions for greedy planting algorithm."""

import math

from core.engine import Engine
from core.garden import Garden
from core.plants.plant import Plant
from core.plants.plant_variety import PlantVariety
from core.point import Position


def calculate_distance(pos1: Position, pos2: Position) -> float:
    """Calculate Euclidean distance between two positions."""
    dx = pos1.x - pos2.x
    dy = pos1.y - pos2.y
    return math.sqrt(dx * dx + dy * dy)


def simulate_and_score(
    garden: Garden, turns: int, w_short: float = 1.0, w_long: float = 1.0
) -> float:
    """
    Run simulation for T turns and return average growth per plant.

    Args:
        garden: Garden with placed plants
        turns: Number of simulation turns
        w_short: Weight for short-term growth (turns 1-5)
        w_long: Weight for long-term growth (turns 6-T)

    Returns:
        Average growth per plant (F(S))
    """
    if len(garden.plants) == 0:
        return 0.0

    # Create a deep copy of the garden to avoid modifying the original
    test_garden = copy_garden(garden)

    # Run simulation
    engine = Engine(test_garden)
    engine.run_simulation(turns)

    # Calculate score with optional weighting
    if turns <= 5:
        # Short simulation, just use final growth
        total_growth = test_garden.total_growth()
    else:
        # Weight short-term vs long-term
        short_term_growth = (
            sum(engine.growth_history[:5])
            if len(engine.growth_history) >= 5
            else sum(engine.growth_history)
        )
        long_term_growth = sum(engine.growth_history[5:]) if len(engine.growth_history) > 5 else 0

        short_contrib = (w_short / 5) * short_term_growth if len(engine.growth_history) >= 5 else 0
        long_contrib = (w_long / max(1, turns - 5)) * long_term_growth if turns > 5 else 0

        total_growth = short_contrib + long_contrib

    # Return average per plant
    return total_growth / len(test_garden.plants)


def copy_garden(garden: Garden) -> Garden:
    """
    Create a deep copy of the garden with all plants.

    Args:
        garden: Original garden

    Returns:
        Deep copy of the garden
    """
    new_garden = Garden(width=garden.width, height=garden.height)

    # Copy all plants
    for plant in garden.plants:
        new_position = Position(x=plant.position.x, y=plant.position.y)
        new_plant = Plant(variety=plant.variety, position=new_position)

        # Copy state
        new_plant.size = plant.size
        new_plant.micronutrient_inventory = plant.micronutrient_inventory.copy()

        new_garden.plants.append(new_plant)
        new_garden._used_varieties.add(id(plant.variety))

    return new_garden


def generate_grid_candidates(garden: Garden, grid_samples: int) -> list[Position]:
    """
    Generate grid of candidate positions for first plant.

    Args:
        garden: Garden to place plants in
        grid_samples: Number of samples per dimension

    Returns:
        List of candidate positions
    """
    candidates = []

    # Calculate grid spacing
    x_step = garden.width / (grid_samples - 1) if grid_samples > 1 else garden.width / 2
    y_step = garden.height / (grid_samples - 1) if grid_samples > 1 else garden.height / 2

    for i in range(grid_samples):
        for j in range(grid_samples):
            x = i * x_step
            y = j * y_step

            # Ensure within bounds
            x = min(x, garden.width)
            y = min(y, garden.height)

            candidates.append(Position(x=int(x), y=int(y)))

    return candidates


def circle_circle_intersection(
    center1: Position, radius1: float, center2: Position, radius2: float
) -> list[Position]:
    """
    Find intersection points of two circles.

    Args:
        center1: Center of first circle
        radius1: Radius of first circle
        center2: Center of second circle
        radius2: Radius of second circle

    Returns:
        List of intersection points (0, 1, or 2 points)
    """
    d = calculate_distance(center1, center2)

    # No intersection cases
    if d > radius1 + radius2:  # Circles too far apart
        return []
    if d < abs(radius1 - radius2):  # One circle inside the other
        return []
    if d == 0 and radius1 == radius2:  # Identical circles
        return []

    # Calculate intersection points
    a = (radius1 * radius1 - radius2 * radius2 + d * d) / (2 * d)
    h = math.sqrt(radius1 * radius1 - a * a) if radius1 * radius1 >= a * a else 0

    # Point on line between centers
    px = center1.x + a * (center2.x - center1.x) / d
    py = center1.y + a * (center2.y - center1.y) / d

    if h == 0:
        # Single intersection (circles are tangent)
        return [Position(x=int(px), y=int(py))]

    # Two intersections
    intersections = [
        Position(
            x=int(px + h * (center2.y - center1.y) / d), y=int(py - h * (center2.x - center1.x) / d)
        ),
        Position(
            x=int(px - h * (center2.y - center1.y) / d), y=int(py + h * (center2.x - center1.x) / d)
        ),
    ]

    return intersections


def generate_geometric_candidates(
    garden: Garden, variety: PlantVariety, angle_samples: int, max_anchor_pairs: int
) -> list[Position]:
    """
    Generate candidate positions using circle-circle intersections and tangency sampling.
    Focus on tight clustering for maximum nutrient exchange.

    Args:
        garden: Current garden with placed plants
        variety: Variety to place
        angle_samples: Number of angles for tangency sampling
        max_anchor_pairs: Maximum pairs of anchors for CCI

    Returns:
        List of candidate positions
    """
    candidates = []

    if len(garden.plants) == 0:
        return []

    # Get plants that can interact with this variety (different species)
    interactable = [p for p in garden.plants if p.variety.species != variety.species]

    # Strategy 1: Circle-circle intersections between interactable plants
    if len(interactable) >= 2:
        num_pairs = 0
        for i in range(len(interactable)):
            for j in range(i + 1, len(interactable)):
                if num_pairs >= max_anchor_pairs:
                    break

                p1 = interactable[i]
                p2 = interactable[j]

                # Interaction zone intersections (for strong interaction)
                # Use slightly tighter radius to ensure strong overlap
                r1_interaction = p1.variety.radius + variety.radius
                r2_interaction = p2.variety.radius + variety.radius
                intersections = circle_circle_intersection(
                    p1.position, r1_interaction * 0.95, p2.position, r2_interaction * 0.95
                )
                candidates.extend(intersections)

                # Also try with full interaction radius
                intersections2 = circle_circle_intersection(
                    p1.position, r1_interaction * 0.8, p2.position, r2_interaction * 0.8
                )
                candidates.extend(intersections2)

                num_pairs += 1

            if num_pairs >= max_anchor_pairs:
                break

    # Strategy 2: Tangency sampling around interactable plants
    # Place new plant JUST within interaction range of existing plants
    if len(interactable) > 0:
        for plant in interactable[:10]:  # Limit to first 10
            interaction_dist = plant.variety.radius + variety.radius

            for i in range(angle_samples):
                angle = 2 * math.pi * i / angle_samples

                # Position at 70-90% of interaction distance for maximum exchange
                for factor in [0.7, 0.8, 0.9]:
                    x = plant.position.x + interaction_dist * factor * math.cos(angle)
                    y = plant.position.y + interaction_dist * factor * math.sin(angle)
                    candidates.append(Position(x=int(round(x)), y=int(round(y))))

    # Strategy 3: If no interactable plants, sample around all plants
    if len(interactable) == 0 and len(garden.plants) > 0:
        for plant in garden.plants[:5]:
            # Use minimum spacing but add a bit for valid placement
            spacing_dist = max(plant.variety.radius, variety.radius)

            for i in range(angle_samples):
                angle = 2 * math.pi * i / angle_samples
                # Place just outside minimum distance
                x = plant.position.x + spacing_dist * 1.05 * math.cos(angle)
                y = plant.position.y + spacing_dist * 1.05 * math.sin(angle)
                candidates.append(Position(x=int(round(x)), y=int(round(y))))

    return candidates


def filter_candidates(
    candidates: list[Position], garden: Garden, tolerance: float
) -> list[Position]:
    """
    Filter candidates to keep only those within bounds and deduplicate.

    Args:
        candidates: List of candidate positions
        garden: Garden bounds
        tolerance: Deduplication tolerance

    Returns:
        Filtered list of candidates
    """
    filtered = []

    for pos in candidates:
        # Check bounds
        if not garden.within_bounds(pos):
            continue

        # Check for duplicates
        is_duplicate = False
        for existing in filtered:
            if calculate_distance(pos, existing) < tolerance:
                is_duplicate = True
                break

        if not is_duplicate:
            filtered.append(pos)

    return filtered


def geometric_heuristic(
    position: Position,
    garden: Garden,
    variety: PlantVariety,
    lambda_interact: float,
    lambda_gap: float,
) -> float:
    """
    Calculate geometric heuristic for pre-ranking candidates.

    Args:
        position: Candidate position
        garden: Current garden
        variety: Variety to place
        lambda_interact: Weight for interaction score
        lambda_gap: Weight for gap penalty

    Returns:
        Heuristic score (higher is better)
    """
    if len(garden.plants) == 0:
        return 0.0

    # Count interactions and calculate interaction quality
    interaction_score = 0.0

    for plant in garden.plants:
        if plant.variety.species != variety.species:
            dist = calculate_distance(position, plant.position)
            interaction_dist = plant.variety.radius + variety.radius

            # Score based on proximity to interaction range
            if dist < interaction_dist:
                # Within interaction range - good!
                proximity = 1.0 - (dist / interaction_dist)
                interaction_score += proximity
            else:
                # Outside but close
                excess = dist - interaction_dist
                if excess < 2.0:
                    interaction_score += 0.5 / (1.0 + excess)

    # Calculate gap penalty (distance to nearest neighbor)
    min_dist = float('inf')
    for plant in garden.plants:
        dist = calculate_distance(position, plant.position)
        min_dist = min(min_dist, dist)

    # Penalize if too far from others
    gap_penalty = min_dist if min_dist < 5.0 else 5.0

    return lambda_interact * interaction_score - lambda_gap * gap_penalty


def evaluate_placement(
    garden: Garden,
    variety: PlantVariety,
    position: Position,
    turns: int,
    beta: float,
    w_short: float,
    w_long: float,
    current_score: float,
) -> tuple[float, float, float]:
    """
    Evaluate placing a variety at a position.

    Args:
        garden: Current garden
        variety: Variety to place
        position: Position to place at
        turns: Simulation turns
        beta: Plant reward weight
        w_short: Short-term weight
        w_long: Long-term weight
        current_score: Current garden score

    Returns:
        Tuple of (total_value, delta_score, plant_reward)
    """
    # Create test garden with new plant
    test_garden = copy_garden(garden)
    test_plant = test_garden.add_plant(variety, position)

    if test_plant is None:
        return float('-inf'), 0.0, 0.0

    # Calculate new score
    new_score = simulate_and_score(test_garden, turns, w_short, w_long)

    # Calculate delta
    delta = new_score - current_score if len(garden.plants) > 0 else new_score

    # Calculate plant reward (new plant's contribution)
    # Note: test_plant in test_garden has been simulated, so it has a size
    new_plant_growth = 0.0
    for plant in test_garden.plants:
        if id(plant.variety) == id(variety):
            new_plant_growth = plant.size
            break

    plant_reward = beta * (new_plant_growth / len(test_garden.plants))

    total_value = delta + plant_reward

    return total_value, delta, plant_reward
