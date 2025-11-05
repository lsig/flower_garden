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
    """Dense-packing strategy that keeps micronutrients balanced while filling space quickly."""

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

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        self._garden = garden
        self._all_varieties = list(varieties)
        self._species_pool = self._build_species_pool(varieties)
        self._grid_step = self._determine_grid_step()
        self._centre = Position(garden.width / 2.0, garden.height / 2.0)

    # Public API ---------------------------------------------------------

    def cultivate(self) -> None:
        if not self._all_varieties:
            return

        candidates = self._build_candidate_positions()
        if not candidates:
            return

        # Kick-start with a central plant if possible to anchor clustering.
        initial_species = self._select_species() or self._fallback_species()
        if initial_species:
            variety = self._take_variety(initial_species)
            if variety:
                centre_position = Position(self._centre.x, self._centre.y)
                planted = self._attempt_direct_placement(variety, [centre_position])
                if planted:
                    self._remove_position_if_present(centre_position, candidates)
                else:
                    self._return_variety(initial_species, variety)

        # Main planting loop: continue until no varieties remain or no space left.
        safety_limit = len(self._all_varieties) * 2
        while safety_limit > 0 and self._has_remaining_varieties():
            safety_limit -= 1

            target_species = self._select_species()
            if target_species is None:
                target_species = self._fallback_species()
            if target_species is None:
                break

            variety = self._take_variety(target_species)
            if variety is None:
                continue

            if self._attempt_clustered_placement(variety, candidates):
                continue

            # Fallback scatter attempts near the densest portion of the garden.
            fallback_position = self._random_interior_spot(variety)
            if fallback_position:
                planted = self._garden.add_plant(variety, fallback_position)
                if planted is not None:
                    self._remove_position_if_present(fallback_position, candidates)
                    continue

            # Could not place the variety; give it back for a later pass.
            self._return_variety(target_species, variety)
            break

    # Variety bookkeeping -----------------------------------------------

    def _build_species_pool(
        self, varieties: Iterable[PlantVariety]
    ) -> dict[Species, deque[PlantVariety]]:
        buckets: dict[Species, list[PlantVariety]] = defaultdict(list)
        for variety in varieties:
            buckets[variety.species].append(variety)

        pool: dict[Species, deque[PlantVariety]] = {}
        for species, bucket in buckets.items():
            bucket.sort(key=self._variety_priority, reverse=True)
            pool[species] = deque(bucket)
        return pool

    def _variety_priority(self, variety: PlantVariety) -> float:
        coeffs = variety.nutrient_coefficients
        produce = coeffs.get(self._SUPPLIES.get(variety.species, Micronutrient.R), 0.0)
        consume = sum(
            abs(coeffs.get(nutrient, 0.0)) for nutrient in self._CONSUMES.get(variety.species, ())
        )

        efficiency = -abs(consume) if produce <= 0.0 else produce / (consume + 1e-6)

        radius_penalty = 1.0 + variety.radius * variety.radius

        # Favour balanced output while penalising larger radii.
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

    # Micronutrient targeting -------------------------------------------

    def _select_species(self) -> Species | None:
        nutrient_totals = self._current_nutrient_totals()

        sorted_deficits = sorted(
            self._NUTRIENT_ORDER,
            key=lambda nutrient: (nutrient_totals[nutrient], self._NUTRIENT_ORDER.index(nutrient)),
        )

        for nutrient in sorted_deficits:
            species = self._species_for_nutrient(nutrient)
            if species and self._species_pool.get(species):
                return species
        return None

    def _current_nutrient_totals(self) -> dict[Micronutrient, float]:
        totals = {nutrient: 0.0 for nutrient in Micronutrient}
        for plant in self._garden.plants:
            for nutrient, amount in plant.variety.nutrient_coefficients.items():
                totals[nutrient] += amount
        return totals

    def _species_for_nutrient(self, nutrient: Micronutrient) -> Species | None:
        for species, produces in self._SUPPLIES.items():
            if produces == nutrient:
                return species
        return None

    # Placement grid ----------------------------------------------------

    def _determine_grid_step(self) -> float:
        if not self._all_varieties:
            return 0.5
        smallest = min(variety.radius for variety in self._all_varieties)
        largest = max(variety.radius for variety in self._all_varieties)
        base = max(0.2, smallest * 0.85)
        # Cushion the step if radii differ widely to prevent invalid placements.
        if largest > smallest * 1.5:
            base *= 1.05
        return base

    def _build_candidate_positions(self) -> list[Position]:
        positions: list[Position] = []
        horizontal = self._grid_step
        vertical = self._grid_step * 0.9

        y = vertical / 2.0
        row = 0
        while y < self._garden.height:
            offset = (horizontal * 0.5) if row % 2 else 0.0
            x = offset + horizontal / 2.0
            while x < self._garden.width:
                positions.append(Position(x, y))
                x += horizontal
            row += 1
            y += vertical

        positions.sort(key=self._centre_distance)
        return positions

    def _remove_position_if_present(self, position: Position, positions: list[Position]) -> None:
        for idx, candidate in enumerate(positions):
            if math.isclose(candidate.x, position.x, abs_tol=1e-6) and math.isclose(
                candidate.y, position.y, abs_tol=1e-6
            ):
                positions.pop(idx)
                return

    # Placement scoring -------------------------------------------------

    def _attempt_clustered_placement(
        self, variety: PlantVariety, candidates: list[Position]
    ) -> bool:
        scored_indices = []
        for idx, position in enumerate(candidates):
            if not self._garden.can_place_plant(variety, position):
                continue
            score = self._position_score(variety, position)
            if score is not None:
                scored_indices.append((score, idx))

        scored_indices.sort(reverse=True)

        for _score, idx in scored_indices:
            position = candidates[idx]
            planted = self._garden.add_plant(variety, position)
            if planted is not None:
                candidates.pop(idx)
                return True
        return False

    def _position_score(self, variety: PlantVariety, position: Position) -> float | None:
        # Encourage higher overlap counts while keeping everything valid.
        neighbor_tension = 0.0
        for plant in self._garden.plants:
            distance = self._euclidean(position, plant.position)
            limit = variety.radius + plant.variety.radius

            if distance < max(variety.radius, plant.variety.radius):
                return None

            if distance < limit + 1e-6 and plant.variety.species != variety.species:
                neighbor_tension += 2.0 + (limit - distance)
            elif distance < limit * 1.2:
                neighbor_tension += 0.5

        compactness_bonus = 1.0 / (1.0 + self._centre_distance(position))
        return neighbor_tension * 5.0 + compactness_bonus

    def _centre_distance(self, position: Position) -> float:
        return self._euclidean(position, self._centre)

    @staticmethod
    def _euclidean(a: Position, b: Position) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return math.hypot(dx, dy)

    # Auxiliary placement helpers --------------------------------------

    def _attempt_direct_placement(
        self, variety: PlantVariety, positions: Iterable[Position]
    ) -> bool:
        for position in positions:
            if self._garden.can_place_plant(variety, position):
                planted = self._garden.add_plant(variety, position)
                if planted is not None:
                    return True
        return False

    def _random_interior_spot(self, variety: PlantVariety, attempts: int = 40) -> Position | None:
        pad = variety.radius * 1.05
        min_x = pad
        max_x = max(pad, self._garden.width - pad)
        min_y = pad
        max_y = max(pad, self._garden.height - pad)

        for _ in range(attempts):
            base_angle = random.uniform(0.0, 2.0 * math.pi)
            radius = random.uniform(0.0, self._grid_step * 2.5)
            centre_x = self._centre.x + math.cos(base_angle) * radius
            centre_y = self._centre.y + math.sin(base_angle) * radius

            x = min(max(centre_x, min_x), max_x)
            y = min(max(centre_y, min_y), max_y)
            candidate = Position(x, y)
            if self._garden.can_place_plant(variety, candidate):
                return candidate
        return None
