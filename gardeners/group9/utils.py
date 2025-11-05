import math

from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species


def calculate_net_production_per_area(variety: PlantVariety) -> float:
    """
    Calculate the net nutrient production per unit area for a variety.
    This is the positive coefficient minus the sum of absolute values of negative coefficients,
    divided by the area (π * radius²).
    """
    coeffs = variety.nutrient_coefficients

    # Find what this variety produces (positive coefficient)
    produced = max(coeffs.values())

    # Sum what it consumes (negative coefficients)
    consumed = sum(abs(c) for c in coeffs.values() if c < 0)

    # Net production
    net = produced - consumed

    # Area
    area = math.pi * (variety.radius**2)

    return net / area


def find_best_producer_per_nutrient(
    varieties: list[PlantVariety],
) -> dict[Micronutrient, PlantVariety] | None:
    """
    Find the best producer variety for each nutrient (R, G, B).
    Best is defined as highest net production per unit area.

    Returns:
        Dictionary mapping each Micronutrient to its best producer variety,
        or None if not all three species are available.
    """
    best_producers = {}

    for nutrient in [Micronutrient.R, Micronutrient.G, Micronutrient.B]:
        # Find the species that produces this nutrient
        if nutrient == Micronutrient.R:
            target_species = Species.RHODODENDRON
        elif nutrient == Micronutrient.G:
            target_species = Species.GERANIUM
        else:  # Micronutrient.B
            target_species = Species.BEGONIA

        # Filter varieties of this species
        producers = [v for v in varieties if v.species == target_species]

        if not producers:
            return None  # Can't proceed without all three species

        # Find the best one by net production per area
        best = max(producers, key=calculate_net_production_per_area)
        best_producers[nutrient] = best

    return best_producers


def check_ratio_viability(
    r_producer: PlantVariety,
    g_producer: PlantVariety,
    b_producer: PlantVariety,
    ratio: tuple[int, int, int],
) -> bool:
    """
    Check if a given ratio (r_count, g_count, b_count) results in net positive for all nutrients.

    Args:
        r_producer: The variety producing R (Rhododendron)
        g_producer: The variety producing G (Geranium)
        b_producer: The variety producing B (Begonia)
        ratio: Tuple of (r_count, g_count, b_count) integers

    Returns:
        True if this ratio results in net positive for all three nutrients
    """
    r_count, g_count, b_count = ratio

    # Calculate total contribution to each nutrient
    total_r = (
        r_count * r_producer.nutrient_coefficients[Micronutrient.R]
        + g_count * g_producer.nutrient_coefficients[Micronutrient.R]
        + b_count * b_producer.nutrient_coefficients[Micronutrient.R]
    )

    total_g = (
        r_count * r_producer.nutrient_coefficients[Micronutrient.G]
        + g_count * g_producer.nutrient_coefficients[Micronutrient.G]
        + b_count * b_producer.nutrient_coefficients[Micronutrient.G]
    )

    total_b = (
        r_count * r_producer.nutrient_coefficients[Micronutrient.B]
        + g_count * g_producer.nutrient_coefficients[Micronutrient.B]
        + b_count * b_producer.nutrient_coefficients[Micronutrient.B]
    )

    # All must be positive
    return total_r > 0 and total_g > 0 and total_b > 0


def find_integer_ratio(
    r_producer: PlantVariety, g_producer: PlantVariety, b_producer: PlantVariety, max_sum: int = 30
) -> tuple[int, int, int]:
    """
    Find the smallest integer ratio (r_count : g_count : b_count) that results in
    net positive production for all nutrients.

    Args:
        r_producer: The variety producing R (Rhododendron)
        g_producer: The variety producing G (Geranium)
        b_producer: The variety producing B (Begonia)
        max_sum: Maximum sum of integers to try (default 30)

    Returns:
        Tuple of (r_count, g_count, b_count) representing the optimal ratio
    """
    # Try small integer combinations, starting with small totals
    # This finds the "simplest" ratio first (e.g., 1:1:1 before 10:10:10)

    for total in range(3, max_sum + 1):
        for r_count in range(1, total):
            for g_count in range(1, total - r_count):
                b_count = total - r_count - g_count
                if b_count < 1:
                    continue

                if check_ratio_viability(
                    r_producer, g_producer, b_producer, (r_count, g_count, b_count)
                ):
                    return (r_count, g_count, b_count)

    # Fallback to equal ratios if nothing found (should not happen with valid configs)
    return (1, 1, 1)


def calculate_target_species_distribution(varieties: list[PlantVariety]) -> dict[Species, float]:
    """
    Calculate optimal percentage of each species based on finding the best producer
    for each nutrient and determining a balanced integer ratio.

    Strategy:
    1. Rank plants that produce each color (R, G, B) by net production per unit area
    2. Select the best producer for each color
    3. Find an integer combination of those 3 plants that is net positive in all nutrients
    4. Return the ratio as target percentages

    Args:
        varieties: List of available plant varieties

    Returns:
        Dictionary mapping each Species to its target percentage (0.0 to 1.0)
    """
    # Step 1: Find the best producer for each nutrient
    best_producers = find_best_producer_per_nutrient(varieties)

    if best_producers is None:
        # Fallback if we don't have all three species
        return {Species.RHODODENDRON: 1 / 3, Species.GERANIUM: 1 / 3, Species.BEGONIA: 1 / 3}

    r_producer = best_producers[Micronutrient.R]
    g_producer = best_producers[Micronutrient.G]
    b_producer = best_producers[Micronutrient.B]

    # Step 2: Find integer ratio that balances all nutrients
    r_count, g_count, b_count = find_integer_ratio(r_producer, g_producer, b_producer)

    # Step 3: Convert to percentages
    total = r_count + g_count + b_count

    return {
        Species.RHODODENDRON: r_count / total,
        Species.GERANIUM: g_count / total,
        Species.BEGONIA: b_count / total,
    }
