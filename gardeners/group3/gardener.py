import math
from collections import defaultdict

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener3(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        # group varieties by similar radius and different species
        grouped_flowers = self._group_varieties()
        # cluster as triangles
        self._cluster_triangularly(grouped_flowers)

    def _group_varieties(self) -> dict:
        """ Group flowers by similar radius and different species """
        # NOTE: groups by species only for now
        groups = defaultdict(list)
        for variety in self.varieties:
            groups[variety.species].append(variety)

        return groups
    
    def _cluster_triangularly(self, grouped_flowers: list[PlantVariety]) -> None:
        """ Cluster selected flowers in a triangular format """
        r_plants = grouped_flowers.get(Species.RHODODENDRON, [])
        g_plants = grouped_flowers.get(Species.GERANIUM, [])
        b_plants = grouped_flowers.get(Species.BEGONIA, [])

        r_index = g_index = b_index = 0

        # place by average radius for now
        avg_radius = (r_plants[0].radius + g_plants[0].radius + b_plants[0].radius) / 3
        triangle_side = avg_radius * 1.1
        cluster_spacing = avg_radius * 2.1
        
        # Calculate how many clusters fit in the garden
        start_x = 0.25
        start_y = 0.25
        nx = int((self.garden.width - start_x) / cluster_spacing) + 1
        ny = int((self.garden.height - start_y) / cluster_spacing) + 1
        
        for i in range(nx):
            for j in range(ny):
                # calculate cluster center
                cx = i * cluster_spacing + start_x
                cy = j * cluster_spacing + start_y
                
                # place in equilateral traingles
                positions = [
                    Position(cx, cy),   # r plant
                    Position(cx + triangle_side, cy),   # g plant
                    Position(cx + triangle_side / 2, cy + triangle_side * math.sin(math.radians(60))),   # b plant
                ]
                
                # place different species of plants - add_plant already checks if valid
                if r_index < len(r_plants) and self.garden.add_plant(r_plants[r_index], positions[0]):
                    r_index += 1
                
                if g_index < len(g_plants) and self.garden.add_plant(g_plants[g_index], positions[1]):
                    g_index += 1
                
                if b_index < len(b_plants) and self.garden.add_plant(b_plants[b_index], positions[2]):
                    b_index += 1