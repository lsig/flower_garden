from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener4(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        # Basic, low-effort placement that keeps plants clustered near the center so
        # micronutrient exchanges are likely when only a few varieties are available.
        prioritized_varieties: list[PlantVariety] = []

        # Ensure we try to plant at least one variety for each species first.
        for species in Species:
            species_varieties = [p for p in self.varieties if p.species == species]
            if species_varieties:
                smallest_radius = min(species_varieties, key=lambda v: v.radius)
                prioritized_varieties.append(smallest_radius)

        remaining_varieties = [p for p in self.varieties if p not in prioritized_varieties]
        # Larger plants need space, so fit them next while the garden is mostly empty.
        prioritized_varieties.extend(sorted(remaining_varieties, key=lambda p: p.radius, reverse=True))

        # Generate integer grid positions, closest to the garden center first.
        width = int(self.garden.width)
        height = int(self.garden.height)
        center_x = width // 2
        center_y = height // 2

        candidate_positions = [
            Position(x=x, y=y)
            for x in range(width + 1)
            for y in range(height + 1)
        ]
        print(candidate_positions)
        candidate_positions.sort(
            key=lambda pos: (pos.x - center_x) ** 2 + (pos.y - center_y) ** 2
        )

        for variety in prioritized_varieties:
            for position in candidate_positions:
                if self.garden.add_plant(variety, position):
                    break
