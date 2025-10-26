from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import List, Tuple, Dict
import math
import random



@dataclass
class Placed:
    x: int
    y: int
    r: int
    species: object
    # track cross-species intersections this node has (counts by species key)
    inter_count: Dict[str, int]

class Gardener4(Gardener): 
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.W = self.garden.width or 16
        self.H = self.garden.height or 10

    def update_interactions(self, placed_nodes: List, new_node: Placed) -> None:

        for node in placed_nodes:
            if node.species.name == new_node.species.name:
                continue

            dx = node.x - new_node.x
            dy = node.y - new_node.y
            distance = math.sqrt(dx * dx + dy * dy)
            interaction_distance = node.r + new_node.r

            if distance < interaction_distance:
                node.inter_count[new_node.species.name] += 1
                new_node.inter_count[node.species.name] += 1
    

    def cultivate_garden(self) -> None:

        def spacing_ok(x:int, y:int, r:int, placed:List[Placed]) -> bool:
            # symmetric rule: d >= max(r_new, r_existing)
            for q in placed:
                if math.hypot(x - q.x, y - q.y) < (max(r, q.r) - 1e-9):
                    return False
            return True

        def circle_circle_overlap_area(r1:float, r2:float, d:float) -> float:
            # closed-form intersection area of two circles
            if d >= r1 + r2:
                return 0.0
            if d <= abs(r1 - r2):
                return math.pi * min(r1, r2) ** 2
            r1sq, r2sq = r1*r1, r2*r2
            alpha = math.acos((d*d + r1sq - r2sq) / (2*d*r1))
            beta  = math.acos((d*d + r2sq - r1sq) / (2*d*r2))
            return r1sq*alpha + r2sq*beta - d*r1*math.sin(alpha)

        def outside_area_estimate(x:int, y:int, r:int, samples:int=256) -> float:
            # Monte-Carlo estimate of circle area outside the rectangle [0,W]×[0,H]
            # (robust, simple; r is small so this is plenty fast)
            if r <= 0:
                return 0.0
            count_out = 0
            for _ in range(samples):
                # polar sampling biased ~uniform area: radius ~ sqrt(u)*r
                u = random.random()
                theta = 2*math.pi*random.random()
                rr = r * math.sqrt(u)
                sx = x + rr * math.cos(theta)
                sy = y + rr * math.sin(theta)
                if not (0 <= sx <= self.W and 0 <= sy <= self.H):
                    count_out += 1
            frac_out = count_out / samples
            return frac_out * (math.pi * r * r)

        def intersecting_nodes(x:int, y:int, r:int, placed:List[Placed]) -> List[Placed]:
            IC = []
            for q in placed:
                if math.hypot(x - q.x, y - q.y) < (r + q.r):
                    IC.append(q)
            return IC

        def species_needed_by(species_key:str) -> set[str]:
            all_s = {"RHODODENDRON", "GERANIUM", "BEGONIA"}
            return all_s - {species_key} if species_key in all_s else all_s

        def pop_variety(split_plants:Dict[str, List[PlantVariety]], species_key:str, radius:int) -> PlantVariety | None:
            arr = split_plants.get(species_key, [])
            for i, v in enumerate(arr):
                if int(v.radius) == int(radius):
                    return arr.pop(i)
            return None

        # directions (cardinals + diagonals)
        DIRS = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
        RADS = [3, 2, 1]

        def candidate_score(x:int, y:int, r:int, placed:List[Placed]) -> tuple[float, float, float]:
            """Return (score, overlap_area, outside_area), score is normalized by circle area."""
            circle_area = math.pi * r * r
            if circle_area <= 0:
                return (0.0, 0.0, 0.0)
            # sum exact overlaps with neighbors
            overlap_area = 0.0
            for q in placed:
                d = math.hypot(x - q.x, y - q.y)
                overlap_area += circle_circle_overlap_area(r, q.r, d)
            # estimate outside area
            outside_area = outside_area_estimate(x, y, r, samples=256)
            score = (overlap_area + outside_area) / circle_area
            # cap to [0,1.2] just in case of numeric noise
            return (min(score, 1.2), overlap_area, outside_area)

        def choose_species(IC: List[Placed], radius: int, split_plants):
            all_s = ["RHODODENDRON", "GERANIUM", "BEGONIA"]
            counts = {s: 0 for s in all_s}
            for q in IC:
                sk = q.species.name
                if sk in counts:
                    counts[sk] += 1

            min_c = min(counts.values()) if counts else 0
            pool = [s for s in all_s if counts[s] == min_c]

            # tie-break: species needed by the IC node with the most intersections
            if len(pool) > 1 and IC:
                busiest = max(IC, key=lambda q: sum(q.inter_count.values()) if q.inter_count else 0)
                needed = {"RHODODENDRON", "GERANIUM", "BEGONIA"} - {busiest.species.name}
                narrowed = [s for s in pool if s in needed]
                if narrowed:
                    pool = narrowed

            # filter by availability without mutating
            def has_var_of_radius(species_key: str, r: int) -> bool:
                arr = split_plants.get(species_key, [])
                return any(int(v.radius) == int(r) for v in arr)

            ordered = [s for s in pool if has_var_of_radius(s, radius)]
            return ordered

        def place_nodes(anchor:Placed, split_plants:Dict[str, List[PlantVariety]], placed:List[Placed]) -> Placed | None:
            """
            Build all (pos, radius) options ordered by percentage intersection score.
            For each option in order:
              - choose species as per rule (min IC counts -> tie-break -> available radius)
              - attempt placement; if success, update interactions and return True
            Fallback: if none succeed, pick best option and place any species that has that radius.
            """
            options = []
            for dx, dy in DIRS:
                for r in RADS:
                    d = max(anchor.r, r)
                    x = anchor.x + d * dx
                    y = anchor.y + d * dy
                    # integer & inside garden
                    if not (0 <= x <= self.W and 0 <= y <= self.H):
                        continue
                    x = int(x); y = int(y)
                    if not spacing_ok(x, y, r, placed):
                        continue
                    IC = intersecting_nodes(x, y, r, placed)
                    score, ov, outa = candidate_score(x, y, r, placed)
                    options.append(((x, y, r), score, IC))

            # sort by highest percentage intersection first
            options.sort(key=lambda t: t[1], reverse=True)

            # Try per your species rule in that order
            for (x, y, r), _, IC in options:
                ordered_species = choose_species(IC, r, split_plants)
                for sk in ordered_species:
                    var = pop_variety(split_plants, sk, r)
                    if var is None:
                        continue
                    pos = Position(x, y)
                    planted = self.garden.add_plant(var, pos)
                    if planted is None:
                        # put back variety if the garden rejects it
                        split_plants[sk].insert(0, var)
                        continue
                    new_node = Placed(x=x, y=y, r=r, species=var.species, inter_count=defaultdict(int))

                    return new_node

            # Fallback: ignore species, place best overlap with any species
            for (x, y, r), _, _ in options:
                for sk in ["RHODODENDRON", "GERANIUM", "BEGONIA"]:
                    var = pop_variety(split_plants, sk, r)
                    if var is None:
                        continue
                    pos = Position(x, y)
                    planted = self.garden.add_plant(var, pos)
                    if planted is None:
                        split_plants[sk].insert(0, var)
                        continue
                    new_node = Placed(x=x, y=y, r=r, species=var.species, inter_count=defaultdict(int))
                    return new_node

            return False

        #Notes: One way to avoid imbalance is by preplacing imbalanced plants in the middle so they are much more accessible to other species.

        placed_nodes: List[Placed] = []

        #start at corner
        init_pos = Position(0, 0) 
                
        #add largest plant at corner
        self.varieties.sort(key=lambda v: v.radius, reverse=True)
        plant = self.varieties.pop(0)
        self.garden.add_plant(plant, init_pos)

        node = Placed(x=init_pos.x, y=init_pos.y, r=plant.radius, species=plant.species, inter_count=defaultdict(int))
        self.update_interactions(placed_nodes, node)
        
        placed_nodes.append(node)
        placeable_nodes: List[Placed] = []
        placeable_nodes.append(node)

        #Split by plant type
        split_plants: Dict[str, List[PlantVariety]] = defaultdict(list)
        for variety in self.varieties:
            split_plants[variety.species.name].append(variety)

        while(True):
            #select plant with least interactions that is placable

            if not placeable_nodes:
                break # out of placeable nodes

            sorted_nodes = sorted(placeable_nodes, key=lambda n: sum(n.inter_count.values()))
            current_node = sorted_nodes[0]

            res = place_nodes(current_node, split_plants, placed_nodes) 

            print(current_node, res)


            if not res:
                placeable_nodes.remove(current_node)
                continue

            self.update_interactions(placed_nodes, res)
            placed_nodes.append(res)
            placeable_nodes.append(res)



            


            



        

        



