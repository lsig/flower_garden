from __future__ import annotations

import math
import random
from collections import defaultdict, deque
from collections.abc import Iterable

from core.garden import Garden
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class TripletStrategy:
    """
    Dense-packing strategy:
    - Fills the garden as much as possible,
    - Encourages cross-species interactions,
    - Keeps micronutrients roughly balanced without overfitting to one config.
    """

    _SUPPLIES = {
        Species.RHODODENDRON: Micronutrient.R,
        Species.GERANIUM: Micronutrient.G,
        Species.BEGONIA: Micronutrient.B,
    }

    _CONSUMES = {
        Species.RHODODENDRON: (Micronutrient.G, Micronutrient.B),
        Species.GERANIUM: (Micronutrient.R, Micronutrient.B),
        Species.BEGONIA: (Micronutrient.R, Micronutrient.G),
    }

    _NUTRIENT_ORDER = (Micronutrient.R, Micronutrient.G, Micronutrient.B)

    # ------------------------------------------------------------------ #
    # Init
    # ------------------------------------------------------------------ #

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        self._garden = garden
        self._all_varieties = list(varieties)
        self._species_pool = self._build_species_pool(varieties)
        self._grid_step = self._determine_grid_step()
        self._centre = Position(garden.width / 2.0, garden.height / 2.0)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def cultivate(self) -> None:
        if not self._all_varieties:
            return

        candidates = self._build_candidate_positions()
        if not candidates:
            return

        # Seed a first plant at center (optional anchor for clustering).
        initial_species = self._select_species() or self._fallback_species()
        if initial_species:
            variety = self._take_variety(initial_species)
            if variety:
                centre_position = Position(self._centre.x, self._centre.y)
                if self._attempt_direct_placement(variety, [centre_position]):
                    self._remove_position_if_present(centre_position, candidates)
                else:
                    self._return_variety(initial_species, variety)

        # Main planting loop:
        # - run while we placed something in the previous pass
        # - stop if no varieties left or safety_limit hit
        safety_limit = len(self._all_varieties) * 5
        placed_any = True

        while placed_any and self._has_remaining_varieties() and safety_limit > 0:
            placed_any = False
            safety_limit -= 1

            target_species = self._select_species() or self._fallback_species()
            if target_species is None:
                break

            variety = self._take_variety(target_species)
            if variety is None:
                continue

            # 1) Try best candidate grid positions (clustered / interactive).
            if self._attempt_clustered_placement(variety, candidates):
                placed_any = True
                continue

            # 2) Fallback: random legal spot anywhere in the interior.
            fallback_position = self._random_interior_spot(variety)
            if fallback_position:
                planted = self._garden.add_plant(variety, fallback_position)
                if planted is not None:
                    self._remove_position_if_present(fallback_position, candidates)
                    placed_any = True
                    continue

            # 3) Could not place this variety right now: put it back; try others.
            self._return_variety(target_species, variety)

        # Stop when:
        # - no varieties remain, OR
        # - one full pass failed to place anything, OR
        # - safety_limit reached.

    # ------------------------------------------------------------------ #
    # Variety bookkeeping
    # ------------------------------------------------------------------ #

    def _build_species_pool(
        self, varieties: Iterable[PlantVariety]
    ) -> dict[Species, deque[PlantVariety]]:
        buckets: dict[Species, list[PlantVariety]] = defaultdict(list)
        for variety in varieties:
            buckets[variety.species].append(variety)

        pool: dict[Species, deque[PlantVariety]] = {}
        for species, bucket in buckets.items():
            # Prioritize efficient, small-radius varieties.
            bucket.sort(key=self._variety_priority, reverse=True)
            pool[species] = deque(bucket)
        return pool

    def _variety_priority(self, variety: PlantVariety) -> float:
        coeffs = variety.nutrient_coefficients
        supply_nutrient = self._SUPPLIES.get(variety.species, Micronutrient.R)
        produce = coeffs.get(supply_nutrient, 0.0)
        consume = sum(abs(coeffs.get(n, 0.0)) for n in self._CONSUMES.get(variety.species, ()))

        efficiency = -abs(consume) if produce <= 0.0 else produce / (consume + 1e-6)

        radius_penalty = 1.0 + variety.radius * variety.radius
        return efficiency / radius_penalty

    def _take_variety(self, species: Species) -> PlantVariety | None:
        pool = self._species_pool.get(species)
        if not pool:
            return None
        return pool.popleft()

    def _return_variety(self, species: Species, variety: PlantVariety) -> None:
        self._species_pool.setdefault(species, deque()).appendleft(variety)

    def _has_remaining_varieties(self) -> bool:
        return any(pool for pool in self._species_pool.values())

    def _fallback_species(self) -> Species | None:
        for species in (Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA):
            if self._species_pool.get(species):
                return species
        return None

    # ------------------------------------------------------------------ #
    # Species selection (general, non-rigged)
    # ------------------------------------------------------------------ #

    def _select_species(self) -> Species | None:
        """
        Generic selector:
        - Bias toward species that fix current micronutrient deficits,
        - Softly reward species that consume surplus,
        - Always keep non-zero probability for each available species.
        """
        available = [s for s, pool in self._species_pool.items() if pool]
        if not available:
            return None

        totals = self._current_nutrient_totals()
        deficits = {m: -totals[m] for m in Micronutrient}

        weights: dict[Species, float] = {}
        base_floor = 0.2  # prevents starvation

        for s in available:
            supply = self._SUPPLIES[s]
            consumes = self._CONSUMES[s]

            w = 0.0

            # Reward fixing deficit in its supplied micronutrient.
            if deficits[supply] > 0:
                w += deficits[supply]

            # Soft reward consuming surplus nutrients.
            surplus_relief = sum(max(0.0, totals[n]) for n in consumes)
            w += 0.3 * surplus_relief

            # Non-zero floor + tiny noise to avoid lock-in.
            weights[s] = base_floor + max(0.0, w) + random.random() * 1e-3

        total_w = sum(weights.values())
        if total_w <= 0:
            return random.choice(available)

        r = random.uniform(0.0, total_w)
        acc = 0.0
        for s in available:
            acc += weights[s]
            if r <= acc:
                return s

        return available[-1]

    def _current_nutrient_totals(self) -> dict[Micronutrient, float]:
        totals = {nutrient: 0.0 for nutrient in Micronutrient}
        for plant in self._garden.plants:
            for nutrient, amount in plant.variety.nutrient_coefficients.items():
                totals[nutrient] += amount
        return totals

    # ------------------------------------------------------------------ #
    # Placement grid
    # ------------------------------------------------------------------ #

    def _determine_grid_step(self) -> float:
        """
        Choose a grid step that:
        - Is small enough for dense packing,
        - Not so tiny that large-radius plants can never fit.
        """
        if not self._all_varieties:
            return 0.5

        smallest = min(v.radius for v in self._all_varieties)
        largest = max(v.radius for v in self._all_varieties)

        # Start near small radii but nudge toward handling big ones too.
        base = max(0.7 * smallest, min(smallest, 0.5 * (smallest + largest)))

        # If radii differ a lot, inflate so big plants aren't auto-blocked.
        if largest > smallest * 1.5:
            base *= 1.2

        return max(base, 0.3)

    def _build_candidate_positions(self) -> list[Position]:
        positions: list[Position] = []
        horizontal = self._grid_step
        vertical = self._grid_step * 0.9

        y = vertical / 2.0
        row = 0
        while y < self._garden.height:
            offset = (horizontal * 0.5) if (row % 2) else 0.0
            x = offset + horizontal / 2.0
            while x < self._garden.width:
                positions.append(Position(x, y))
                x += horizontal
            row += 1
            y += vertical

        # Prefer positions near center for compactness.
        positions.sort(key=self._centre_distance)
        return positions

    def _remove_position_if_present(self, position: Position, positions: list[Position]) -> None:
        for idx, candidate in enumerate(positions):
            if math.isclose(candidate.x, position.x, abs_tol=1e-6) and math.isclose(
                candidate.y, position.y, abs_tol=1e-6
            ):
                positions.pop(idx)
                return

    # ------------------------------------------------------------------ #
    # Placement scoring & clustered placement
    # ------------------------------------------------------------------ #

    def _attempt_clustered_placement(
        self, variety: PlantVariety, candidates: list[Position]
    ) -> bool:
        scored_indices: list[tuple[float, int]] = []

        for idx, position in enumerate(candidates):
            if not self._garden.can_place_plant(variety, position):
                continue
            score = self._position_score(variety, position)
            if score is not None:
                scored_indices.append((score, idx))

        if not scored_indices:
            return False

        scored_indices.sort(reverse=True)

        for _score, idx in scored_indices:
            position = candidates[idx]
            planted = self._garden.add_plant(variety, position)
            if planted is not None:
                candidates.pop(idx)
                return True

        return False

    def _position_score(self, variety: PlantVariety, position: Position) -> float | None:
        """
        Score a candidate:
        - Reject if violates min centre-distance,
        - Reward cross-species neighbors within interaction range,
        - Mild reward for being near others (compactness).
        """
        neighbor_tension = 0.0

        for plant in self._garden.plants:
            distance = self._euclidean(position, plant.position)
            limit = variety.radius + plant.variety.radius

            # Hard constraint: no overlapping cores.
            if distance < max(variety.radius, plant.variety.radius):
                return None

            # Strong bonus: cross-species neighbors in interaction range.
            if distance <= limit and plant.variety.species != variety.species:
                neighbor_tension += 2.0 + (limit - distance)
            # Soft bonus: generic nearby neighbor.
            elif distance < limit * 1.2:
                neighbor_tension += 0.5

        compactness_bonus = 1.0 / (1.0 + self._centre_distance(position))
        return neighbor_tension * 5.0 + compactness_bonus

    # ------------------------------------------------------------------ #
    # Geometry helpers
    # ------------------------------------------------------------------ #

    def _centre_distance(self, position: Position) -> float:
        return self._euclidean(position, self._centre)

    @staticmethod
    def _euclidean(a: Position, b: Position) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return math.hypot(dx, dy)

    # ------------------------------------------------------------------ #
    # Auxiliary placement helpers
    # ------------------------------------------------------------------ #

    def _attempt_direct_placement(
        self, variety: PlantVariety, positions: Iterable[Position]
    ) -> bool:
        for position in positions:
            if self._garden.can_place_plant(variety, position):
                planted = self._garden.add_plant(variety, position)
                if planted is not None:
                    return True
        return False

    def _random_interior_spot(self, variety: PlantVariety, attempts: int = 80) -> Position | None:
        """
        Fallback: try random positions anywhere in the valid interior.
        """
        pad = variety.radius * 1.05
        min_x = pad
        max_x = self._garden.width - pad
        min_y = pad
        max_y = self._garden.height - pad

        if min_x >= max_x or min_y >= max_y:
            return None

        for _ in range(attempts):
            x = random.uniform(min_x, max_x)
            y = random.uniform(min_y, max_y)
            candidate = Position(x, y)
            if self._garden.can_place_plant(variety, candidate):
                return candidate

        return None
