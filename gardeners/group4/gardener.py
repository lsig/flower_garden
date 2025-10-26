import math
import random
from collections import defaultdict
from dataclasses import dataclass

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position


@dataclass
class Placed:
    x: int
    y: int
    r: int
    species: object
    inter_count: dict[str, int]

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

    def _spacing_ok(self, x: int, y: int, r: int, placed: list[Placed]) -> bool:
        for q in placed:
            d = math.hypot(x - q.x, y - q.y)
            if d < (max(r, q.r)):
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

    def _outside_area_est(self, x: int, y: int, r: int, samples: int = 128) -> float:
        if r <= 0:
            return 0.0
        out = 0
        for _ in range(samples):
            u, t = random.random(), 2 * math.pi * random.random()
            rr = r * math.sqrt(u)
            sx, sy = x + rr * math.cos(t), y + rr * math.sin(t)
            if not (0 <= sx <= self.W and 0 <= sy <= self.H):
                out += 1
        return (out / samples) * (math.pi * r * r)

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

    def _place_from(
        self, anchor: Placed, inv: dict[str, list[PlantVariety]], placed: list[Placed]
    ) -> Placed | None:
        # Gather all candidate (dir, r) positions + per-species options (only if inventory has that radius)
        options: list[tuple[int, float, int, str, int, int]] = []
        # tuple = (missing_filled, score, radius, species_key, x, y)

        for dx, dy in self.DIRS:
            for r in self.RADS:
                d = max(anchor.r, r)
                x, y = anchor.x + d * dx, anchor.y + d * dy
                if not (0 <= x <= self.W and 0 <= y <= self.H):
                    continue
                x, y = int(x), int(y)
                if not self._spacing_ok(x, y, r, placed):
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

        print(options)

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

            node = Placed(x=x, y=y, r=r, species=var.species, inter_count=defaultdict(int))
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

    def cultivate_garden(self) -> None:
        if not self.varieties:
            return

        # intialize largest at (w/2,h/2). In the future when plant varieties are imbalanced,
        # preplacing lacking varieties spread out around the middle might be helpful

        self.varieties.sort(key=lambda v: v.radius)
        inv = self._split_by_species(self.varieties[1:])
        seed = self.varieties[0]
        if self.garden.add_plant(seed, Position(self.W / 2, self.H / 2)) is not None:
            seed_node = Placed(
                self.W / 2, self.H / 2, int(seed.radius), seed.species, defaultdict(int)
            )

        placed = [seed_node]
        placeable = [seed_node]

        while placeable and len(placed) < len(self.varieties):

            def missing_species_count(node: Placed) -> int:
                """Return how many required species this node is still missing."""
                required = {'RHODODENDRON', 'GERANIUM', 'BEGONIA'} - {node.species.name}
                missing = sum(1 for s in required if node.inter_count.get(s, 0) == 0)
                return missing

            def remaining_for_species(sk: str) -> int:
                # total remaining varieties for this species across all radii
                arr = inv.get(sk, [])
                return len(arr)

            # prioritize nodes missing the most species, then those with fewest interactions
            placeable.sort(
                key=lambda n: (
                    -missing_species_count(n),
                    -remaining_for_species(n.species.name),
                    sum(n.inter_count.values()),
                )
            )

            anchor = placeable[0]
            new_node = self._place_from(anchor, inv, placed)
            if new_node is None:
                placeable.pop(0)
                continue
            placeable.append(new_node)

        species_counts = defaultdict(int)
        for p in placed:
            species_counts[p.species.name] += 1

        print(
            f'Current totals — '
            f'Rhododendron: {species_counts["RHODODENDRON"]}, '
            f'Geranium: {species_counts["GERANIUM"]}, '
            f'Begonia: {species_counts["BEGONIA"]}, '
            f'Total: {len(placed)}'
        )
        print('-' * 60)
