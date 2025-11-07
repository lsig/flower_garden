import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass

from core.engine import Engine
from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position
from gardeners.group4 import rectangular, smaller_configs


@dataclass
class Placed:
    x: int
    y: int
    r: int
    species: object
    inter_count: dict[str, int]
    plant: PlantVariety

    def __repr__(self):
        return f'<{self.species.name} ({self.x},{self.y}) r={self.r}>'


class Gardener4(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.W = int(getattr(self.garden, 'width', 16) or 16)
        self.H = int(getattr(self.garden, 'height', 10) or 10)
        self.DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (-1, 1), (1, -1)]
        self.RADS = [3, 2, 1]
        self.ALL_SPECIES = ['RHODODENDRON', 'GERANIUM', 'BEGONIA']
        self.debug = False

    def _spacing_ok(self, x: int, y: int, r: int, placed: list[Placed]) -> bool:
        for q in placed:
            d = math.hypot(x - q.x, y - q.y)
            if d < max(r, q.r):
                return False
        return True

    def _overlap_area(self, r1: float, r2: float, d: float) -> float:
        if d >= r1 + r2:
            return 0.0
        if d <= abs(r1 - r2):
            return math.pi * min(r1, r2) ** 2
        r1s, r2s = r1 * r1, r2 * r2
        a = math.acos((d * d + r1s - r2s) / (2 * d * r1))
        b = math.acos((d * d + r2s - r1s) / (2 * d * r2))
        return r1s * a + r2s * b - d * r1 * math.sin(a)

    def _outside_area_est(self, x: int, y: int, r: int, samples: int = 3) -> float:
        if r <= 0:
            return 0.0

        n_r = int(math.sqrt(samples))  # radial divisions
        n_t = int(samples / n_r) or 1  # angular divisions
        out = 0

        for i in range(n_r):
            # even spacing
            u = (i + 0.5) / n_r
            rr = r * math.sqrt(u)
            for j in range(n_t):
                theta = 2 * math.pi * (j + 0.5) / n_t
                sx = x + rr * math.cos(theta)
                sy = y + rr * math.sin(theta)
                if not (0 <= sx <= self.W and 0 <= sy <= self.H):
                    out += 1

        total_samples = n_r * n_t
        return (out / total_samples) * (math.pi * r * r)

    def _score_candidate(self, x: int, y: int, r: int, placed: list[Placed]) -> float:
        area = math.pi * r * r
        if area <= 0:
            return 0.0
        overlap = sum(self._overlap_area(r, q.r, math.hypot(x - q.x, y - q.y)) for q in placed)
        outside = self._outside_area_est(x, y, r)
        return min((overlap + outside) / area, 1.2)

    # returns instersecting plants
    def _intersecting(self, x: int, y: int, r: int, placed: list[Placed]) -> list[Placed]:
        return [q for q in placed if math.hypot(x - q.x, y - q.y) < (r + q.r)]

    # updates intersection counts
    def _update_interactions(self, placed_nodes: list[Placed], new_node: Placed) -> None:
        for node in placed_nodes:
            if node.species.name == new_node.species.name:
                continue
            if math.hypot(node.x - new_node.x, node.y - new_node.y) < (node.r + new_node.r):
                node.inter_count[new_node.species.name] += 1
                new_node.inter_count[node.species.name] += 1

    def _split_by_species(self, varieties: list[PlantVariety]) -> dict[str, list[PlantVariety]]:
        buckets: dict[str, list[PlantVariety]] = defaultdict(list)
        for v in varieties:
            buckets[v.species.name].append(v)
        return buckets

    def _has_radius(self, inv: dict[str, list[PlantVariety]], sk: str, r: int) -> bool:
        return any(int(v.radius) == int(r) for v in inv.get(sk, []))

    def _pop_variety(
        self, inv: dict[str, list[PlantVariety]], sk: str, r: int
    ) -> PlantVariety | None:
        arr = inv.get(sk, [])
        for i, v in enumerate(arr):
            if int(v.radius) == int(r):
                return arr.pop(i)
        return None

    # returns species needed by type sk. ex. needed by BEGONIA {'GERANIUM', 'RHODODENDRON'}
    def _species_needed_by(self, sk: str) -> set[str]:
        s = set(self.ALL_SPECIES)
        return s - {sk} if sk in s else s

    def _missing_filled(self, IC: list[Placed], species_key: str) -> int:
        # how many intersecting plants currently have zero intersections with species_key

        sum = 0

        for q in IC:
            if q.species.name != species_key:
                if q.inter_count.get(species_key, 0) == 0:
                    sum += 1
                else:
                    sum += 0.1

        return sum

    def _to_xy(self, x: float, y: float, angle: float, distance: float) -> tuple[float, float]:
        x = x + distance * math.cos(angle)
        y = y + distance * math.sin(angle)
        return x, y

    def _place_from(
        self,
        anchor: Placed,
        inv: dict[str, list[PlantVariety]],
        placed: list[Placed],
        angle_steps: int,
    ) -> Placed | None:
        # Gather all candidate (dir, r) positions + per-species options (only if inventory has that radius)
        options: list[tuple[int, float, int, str, int, int]] = []
        # tuple = (missing_filled, score, radius, species_key, x, y)

        for r in self.RADS:
            # choose points around the anchor
            # angle_steps = 1440

            d = max(anchor.r, r)
            scaled_steps = int(angle_steps + 0.5 * (len(placed) / 50))
            points = [
                self._to_xy(anchor.x, anchor.y, i * (2 * math.pi / scaled_steps), d)
                for i in range(scaled_steps)
            ]

            # print(f'Generated {len(points)} candidate points around anchor {anchor.species.name} at ({anchor.x},{anchor.y}) with radius {r}')

            for x, y in points:
                if not (0 <= x <= self.W and 0 <= y <= self.H) or not self._spacing_ok(
                    x, y, r, placed
                ):
                    continue

                IC = self._intersecting(x, y, r, placed)
                score = self._score_candidate(x, y, r, placed)
                random.shuffle(self.ALL_SPECIES)
                for sk in self.ALL_SPECIES:
                    if not self._has_radius(inv, sk, r):
                        continue
                    missing_filled = self._missing_filled(IC, sk)
                    options.append((missing_filled, score, r, sk, x, y))

        if not options:
            return None

        # Priority: fill most gaps, then best score, then smallest radius
        options.sort(key=lambda t: (-t[0], -t[1], t[2]))

        for _, _, r, sk, x, y in options:
            var = self._pop_variety(inv, sk, r)
            if not var:
                continue
            pos = Position(x, y)
            if self.garden.add_plant(var, pos) is None:
                inv[sk].insert(0, var)  # undo
                continue

            node = Placed(
                x=x, y=y, r=r, species=var.species, inter_count=defaultdict(int), plant=var
            )
            self._update_interactions(placed, node)
            placed.append(node)

            neighbors = [
                q
                for q in placed
                if q is not node and math.hypot(q.x - node.x, q.y - node.y) < (q.r + node.r)
            ]

            # Build readable neighbor summary
            neighbor_info = []
            for nb in neighbors:
                # show neighbor species and how many intersections they have with this node’s type
                count = nb.inter_count.get(node.species.name, 0)
                neighbor_info.append(
                    f'{nb.species.name}(r={nb.r}, x={nb.x}, y={nb.y}, intersections={count})'
                )

            if self.debug:
                print(
                    f'Placed {var.species.name} at ({x},{y}) r={r} for anchor {anchor.species.name} at ({anchor.x},{anchor.y})'
                )

                if neighbor_info:
                    print('  Neighbors:')
                    for info in neighbor_info:
                        print('   -', info)
                else:
                    print('  No neighbors (isolated placement).')
            return node
        return None

    def sort_plants_score(self):
        self.varieties.sort(
            key=lambda v: (
                sum(v.nutrient_coefficients.values()) / (v.radius**2),
                max(v.nutrient_coefficients.values())
                / abs(
                    sum(v.nutrient_coefficients.values()) - max(v.nutrient_coefficients.values())
                ),
            ),
            reverse=True,
        )

    def cultivate_garden(self) -> None:
        time_limit = 55.0
        timer_start = time.time()

        if not self.varieties:
            return

        if len(self.varieties) < 15:
            smaller_gardener = smaller_configs.Gardener4(self.garden, self.varieties)
            smaller_gardener.cultivate_garden()
            return

        radii = {int(v.radius) for v in self.varieties}
        coeff_patterns = [tuple(v.nutrient_coefficients.values()) for v in self.varieties]
        diff = sum(coeff_patterns[0])
        all_same_magnitude = True
        for c in coeff_patterns:
            if abs(sum(c) != diff) > 1e-5:
                all_same_magnitude = False
                break
        if len(radii) == 1 and all_same_magnitude:
            rectagular_gardener = rectangular.Gardener4(self.garden, self.varieties)
            rectagular_gardener.cultivate_garden()
            return

        # intialize largest at (w/2,h/2). In the future when plant varieties are imbalanced,
        # preplacing lacking varieties spread out around the middle might be helpful
        self.varieties.sort(key=lambda v: v.radius)
        self.sort_plants_score()

        placed_best = []
        max_score = 0
        for sign in [-1, 1]:
            if time.time() - timer_start > time_limit:
                break
            for angle_steps in range(710, 730):
                if time.time() - timer_start > time_limit:
                    break
                inv = self._split_by_species(self.varieties[1:])
                seed = self.varieties[0]
                if self.garden.add_plant(seed, Position(self.W / 2, self.H / 2)) is not None:
                    seed_node = Placed(
                        self.W / 2,
                        self.H / 2,
                        int(seed.radius),
                        seed.species,
                        defaultdict(int),
                        seed,
                    )

                placed = [seed_node]
                placeable = [seed_node]

                while placeable and len(placed) < len(self.varieties):

                    def missing_species_count(node: Placed) -> int:
                        """Return how many required species this node is still missing."""
                        required = {'RHODODENDRON', 'GERANIUM', 'BEGONIA'} - {node.species.name}
                        missing = sum(1 for s in required if node.inter_count.get(s, 0) == 0)
                        return missing

                    def remaining_for_species(inv, sk: str) -> int:
                        # total remaining varieties for this species across all radii
                        arr = inv.get(sk, [])
                        return len(arr)

                    # prioritize nodes missing the most species, then those with fewest interactions
                    placeable.sort(
                        key=lambda n: (
                            missing_species_count(n),
                            -remaining_for_species(inv, n.species.name),
                            sign * sum(n.inter_count.values()),
                        )
                    )

                    anchor = placeable[0]
                    new_node = self._place_from(anchor, inv, placed, angle_steps)
                    if new_node is None:
                        placeable.pop(0)
                        continue
                    placeable.append(new_node)

                species_counts = defaultdict(int)
                for p in placed:
                    species_counts[p.species.name] += 1

                if self.debug:
                    print(
                        f'Current totals — '
                        f'Rhododendron: {species_counts["RHODODENDRON"]}, '
                        f'Geranium: {species_counts["GERANIUM"]}, '
                        f'Begonia: {species_counts["BEGONIA"]}, '
                        f'Total: {len(placed)}'
                    )
                    print('-' * 60)

                # tested with 5000 (random and configA.json), the same result
                turns = 900

                score = self.simulate_total_score(turns)

                if self.debug:
                    print(score)
                    print(angle_steps)
                    print(len(placed))
                    print('Area of placed plants: ', sum([100 * ((p.r) ** 2) for p in placed]))

                if score > max_score:
                    max_score = score
                    placed_best = placed

                self.empty_garden()

        for p in placed_best:
            pos = Position(p.x, p.y)
            self.garden.add_plant(p.plant, pos)

    def simulate_total_score(self, turns: int) -> float:
        engine = Engine(self.garden)
        growth_history = engine.run_simulation(turns)
        # print(growth_history[-1])
        return growth_history[-1]

    def empty_garden(self):
        self.garden.plants = []
        self.garden._used_varieties = set()
