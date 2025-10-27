import math

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener9(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def get_production_value(self, variety: PlantVariety) -> float:
        """Get the positive nutrient production value for a variety"""
        if variety.species == Species.RHODODENDRON:
            return variety.nutrient_coefficients[Micronutrient.R]
        elif variety.species == Species.GERANIUM:
            return variety.nutrient_coefficients[Micronutrient.G]
        elif variety.species == Species.BEGONIA:
            return variety.nutrient_coefficients[Micronutrient.B]
        return 0

    def cultivate_garden(self) -> None:
        # Find the variety with highest production
        best_producer = max(self.varieties, key=self.get_production_value)

        # find the center of the garden
        center_x = self.garden.width / 2
        center_y = self.garden.height / 2
        center_pos = Position(center_x, center_y)

        # Place best producer in the center
        if self.garden.can_place_plant(best_producer, center_pos):
            self.garden.add_plant(best_producer, center_pos)

        # complementary varieties
        other_varieties = [v for v in self.varieties if v != best_producer]

        # FIRST RING: Place plants around center
        first_ring_positions = []  # Store positions for second ring

        if len(other_varieties) >= 1:
            for variety in other_varieties:
                # Calculate tight ring radius for interaction with center
                ring_radius = max(best_producer.radius, variety.radius) + 0.1

                # (hexagonal pattern)
                num_plants = 6
                angle_increment = 2 * math.pi / num_plants

                for i in range(num_plants):
                    angle = i * angle_increment
                    x = center_x + ring_radius * math.cos(angle)
                    y = center_y + ring_radius * math.sin(angle)
                    pos = Position(x, y)

                    if self.garden.can_place_plant(variety, pos):
                        plant = self.garden.add_plant(variety, pos)
                        if plant:
                            # Store this position and angle for second ring
                            first_ring_positions.append(
                                {'x': x, 'y': y, 'angle': angle, 'variety': variety}
                            )

        # SECOND RING: Place plants around each first ring plant
        if len(first_ring_positions) > 0:
            for ring_plant in first_ring_positions:
                # Get complementary varieties (different from the ring plant)
                complementary = [v for v in self.varieties if v != ring_plant['variety']]

                for variety in complementary:
                    # Calculate radius from first ring plant
                    sub_ring_radius = max(ring_plant['variety'].radius, variety.radius) + 0.1

                    # Place 2-3 plants around each first ring plant
                    # Offset angles to create a spiral pattern
                    num_sub_plants = 2
                    base_angle = ring_plant['angle']  # Continue the radial direction

                    for j in range(num_sub_plants):
                        # Spread plants at angles perpendicular to radial direction
                        angle_offset = (j - 0.5) * (math.pi / 3)  # ±60 degrees
                        angle = base_angle + angle_offset

                        x = ring_plant['x'] + sub_ring_radius * math.cos(angle)
                        y = ring_plant['y'] + sub_ring_radius * math.sin(angle)
                        pos = Position(x, y)

                        if self.garden.can_place_plant(variety, pos):
                            self.garden.add_plant(variety, pos)

        # fill gaps
        sorted_varieties = sorted(self.varieties, key=lambda v: v.radius)

        # smallest variety first to fill gaps
        small_variety = sorted_varieties[0]
        spacing = small_variety.radius * 2 + 0.2

        x = small_variety.radius + 0.5
        while x < self.garden.width - small_variety.radius:
            y = small_variety.radius + 0.5
            while y < self.garden.height - small_variety.radius:
                pos = Position(x, y)
                if self.garden.can_place_plant(small_variety, pos):
                    self.garden.add_plant(small_variety, pos)
                y += spacing
            x += spacing

        # larger varieties next
        for variety in sorted_varieties[1:]:
            # Try a grid of positions
            step = variety.radius * 1.5
            x = variety.radius

            while x < self.garden.width - variety.radius:
                y = variety.radius
                while y < self.garden.height - variety.radius:
                    pos = Position(x, y)
                    if self.garden.can_place_plant(variety, pos):
                        self.garden.add_plant(variety, pos)
                    y += step
                x += step
