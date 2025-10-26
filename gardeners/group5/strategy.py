from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from core.engine import Engine
from core.garden import Garden
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class TripletStrategy:
    """
    Group 5 strategy: builds small R-G-B clusters (triads) with inter-plant
    distances near the inter-species interaction threshold to keep neighbor
    degree low (2-3), which helps with the 1/4-offer splitting rule.
    """

    # ---------------------------
    # Robust accessors (dict or PlantVariety)
    # ---------------------------

    @staticmethod
    def _get_name(v: Any) -> str:
        if isinstance(v, dict):
            return str(v.get('name', 'VAR'))
        return getattr(v, 'name', 'VAR')

    @staticmethod
    def _get_species(v: Any) -> str:
        if isinstance(v, dict):
            s = v.get('species', 'UNKNOWN')
            return str(getattr(s, 'name', s)).upper()
        s = getattr(v, 'species', 'UNKNOWN')
        return str(getattr(s, 'name', s)).upper()

    @staticmethod
    def _get_species_enum(v: Any) -> Species:
        if isinstance(v, dict):
            s = v.get('species', Species.RHODODENDRON)
            if isinstance(s, Species):
                return s
            return Species[str(s).upper()]
        s = getattr(v, 'species', Species.RHODODENDRON)
        if isinstance(s, Species):
            return s
        return Species[str(s).upper()]

    @staticmethod
    def _get_radius(v: Any) -> float:
        if isinstance(v, dict):
            return float(v.get('radius', 1.0))
        return float(getattr(v, 'radius', 1.0))

    @staticmethod
    def _get_coeff_vector(v: Any) -> tuple[float, float, float]:
        if isinstance(v, dict):
            coeffs = v.get('nutrient_coefficients', {})
            return (
                float(coeffs.get('R', 0.0)),
                float(coeffs.get('G', 0.0)),
                float(coeffs.get('B', 0.0)),
            )
        coeffs = getattr(v, 'nutrient_coefficients', {})
        if Micronutrient.R in coeffs:
            return (
                float(coeffs[Micronutrient.R]),
                float(coeffs[Micronutrient.G]),
                float(coeffs[Micronutrient.B]),
            )
        return (0.0, 0.0, 0.0)

    def _make_variety_key(self, variety: Any) -> tuple[Any, ...]:
        coeffs = tuple(round(c, 3) for c in self._get_coeff_vector(variety))
        return (
            self._get_species_enum(variety).name,
            round(self._get_radius(variety), 3),
            coeffs,
            self._get_name(variety),
        )

    # ---------------------------
    # Internal helpers / structs
    # ---------------------------

    @dataclass
    class _Placement:
        idx: int
        x: float
        y: float

    @dataclass
    class _VarType:
        key: tuple[Any, ...]
        species: Species
        radius: float
        prototype: PlantVariety
        indices: list[int]
        used: int = 0

        def reserve(self) -> int | None:
            if self.used >= len(self.indices):
                return None
            idx = self.indices[self.used]
            self.used += 1
            return idx

        @property
        def available(self) -> int:
            return max(0, len(self.indices) - self.used)

    @dataclass
    class _TripletEval:
        key: tuple[tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]
        total_growth: float
        per_species_growth: dict[Species, float]
        sustaining: bool
        relative_positions: dict[Species, tuple[float, float]]
        cluster_extent: float
        pair_distances: dict[tuple[Species, Species], float]

    @dataclass
    class _TripletPlan:
        r_type: TripletStrategy._VarType
        g_type: TripletStrategy._VarType
        b_type: TripletStrategy._VarType
        layout: TripletStrategy._TripletEval
        indices: dict[Species, int]

    class _SpatialHash:
        """Uniform grid spatial hash for fast neighborhood checks."""

        def __init__(self, cell_size: float, width: float, height: float, get_radius, get_species):
            self.cell = max(0.25, cell_size)
            self.width = width
            self.height = height
            self.get_radius = get_radius
            self.get_species = get_species
            self.grid: dict[tuple[int, int], list[TripletStrategy._Placement]] = defaultdict(list)

        def _key(self, x: float, y: float) -> tuple[int, int]:
            return (int(x // self.cell), int(y // self.cell))

        def _neighbor_keys(self, x: float, y: float, radius: float) -> Iterable[tuple[int, int]]:
            cr = int(math.ceil((radius + self.cell) / self.cell))
            cx, cy = self._key(x, y)
            for dx in range(-cr, cr + 1):
                for dy in range(-cr, cr + 1):
                    yield (cx + dx, cy + dy)

        @staticmethod
        def _min_center_distance(a_r: float, b_r: float) -> float:
            return max(a_r, b_r)

        @staticmethod
        def _cross_too_close(
            allow_cross: bool,
            a_species: Species,
            b_species: Species,
            dist_sq: float,
            a_r: float,
            b_r: float,
        ) -> bool:
            if allow_cross:
                return False
            if a_species == b_species:
                return False
            threshold = a_r + b_r
            return dist_sq < (threshold * threshold)

        def can_place(
            self,
            cand: TripletStrategy._Placement,
            varieties: list[Any],
            extras: list[TripletStrategy._Placement] | None = None,
            allow_cross_existing: bool = False,
            allow_cross_extras: bool = True,
        ) -> bool:
            if not (0.0 <= cand.x <= self.width and 0.0 <= cand.y <= self.height):
                return False
            a_r = self.get_radius(varieties[cand.idx])
            a_species = self.get_species(varieties[cand.idx])
            for key in self._neighbor_keys(cand.x, cand.y, a_r + self.cell):
                for p in self.grid.get(key, []):
                    b_r = self.get_radius(varieties[p.idx])
                    b_species = self.get_species(varieties[p.idx])
                    dx = cand.x - p.x
                    dy = cand.y - p.y
                    d2 = dx * dx + dy * dy
                    md = self._min_center_distance(a_r, b_r)
                    if d2 < md * md:
                        return False
                    if self._cross_too_close(
                        allow_cross_existing, a_species, b_species, d2, a_r, b_r
                    ):
                        return False
            if extras:
                for p in extras:
                    if p.idx == cand.idx and p.x == cand.x and p.y == cand.y:
                        continue
                    b_r = self.get_radius(varieties[p.idx])
                    b_species = self.get_species(varieties[p.idx])
                    dx = cand.x - p.x
                    dy = cand.y - p.y
                    d2 = dx * dx + dy * dy
                    md = self._min_center_distance(a_r, b_r)
                    if d2 < md * md:
                        return False
                    if self._cross_too_close(
                        allow_cross_extras, a_species, b_species, d2, a_r, b_r
                    ):
                        return False
            return True

        def add(self, p: TripletStrategy._Placement) -> None:
            self.grid[self._key(p.x, p.y)].append(p)

    # ---------------------------
    # Public API
    # ---------------------------

    def _build_type_groups(self, rng: random.Random) -> dict[Species, list[TripletStrategy._VarType]]:
        groups: dict[tuple[Any, ...], TripletStrategy._VarType] = {}
        for idx, variety in enumerate(self.varieties):
            key = self._make_variety_key(variety)
            if key not in groups:
                groups[key] = self._VarType(
                    key=key,
                    species=self._get_species_enum(variety),
                    radius=self._get_radius(variety),
                    prototype=variety,
                    indices=[],
                )
            groups[key].indices.append(idx)

        by_species: dict[Species, list[TripletStrategy._VarType]] = {
            Species.RHODODENDRON: [],
            Species.GERANIUM: [],
            Species.BEGONIA: [],
        }

        for var_type in groups.values():
            rng.shuffle(var_type.indices)
            by_species.setdefault(var_type.species, []).append(var_type)

        for species_list in by_species.values():
            species_list.sort(key=lambda vt: (vt.radius, vt.prototype.name))

        return by_species

    @staticmethod
    def _interaction_distance(a_r: float, b_r: float) -> float:
        min_d = max(a_r, b_r)
        target = 0.92 * (a_r + b_r)
        dist = max(min_d, target)
        return min(dist, (a_r + b_r) - 1e-3)

    def _compute_triangle_distances(
        self,
        r_var: PlantVariety,
        g_var: PlantVariety,
        b_var: PlantVariety,
    ) -> dict[tuple[Species, Species], float] | None:
        pairs = [
            (
                Species.RHODODENDRON,
                Species.GERANIUM,
                self._get_radius(r_var),
                self._get_radius(g_var),
            ),
            (
                Species.RHODODENDRON,
                Species.BEGONIA,
                self._get_radius(r_var),
                self._get_radius(b_var),
            ),
            (Species.GERANIUM, Species.BEGONIA, self._get_radius(g_var), self._get_radius(b_var)),
        ]

        distances: list[float] = []
        mins: list[float] = []
        maxs: list[float] = []
        for _, _, ra, rb in pairs:
            dist = self._interaction_distance(ra, rb)
            distances.append(dist)
            mins.append(max(ra, rb))
            maxs.append((ra + rb) - 1e-3)

        for _ in range(10):
            adjusted = False
            for i in range(3):
                others = distances[(i + 1) % 3] + distances[(i + 2) % 3]
                if distances[i] >= others:
                    distances[i] = min(maxs[i], max(mins[i], others - 1e-3))
                    adjusted = True
            if not adjusted:
                break

        if any(distances[i] < mins[i] for i in range(3)):
            return None

        return {
            (pairs[0][0], pairs[0][1]): distances[0],
            (pairs[1][0], pairs[1][1]): distances[1],
            (pairs[2][0], pairs[2][1]): distances[2],
        }

    @staticmethod
    def _solve_triangle_geometry(
        distances: dict[tuple[Species, Species], float],
    ) -> dict[Species, tuple[float, float]] | None:
        d_rg = distances[(Species.RHODODENDRON, Species.GERANIUM)]
        d_rb = distances[(Species.RHODODENDRON, Species.BEGONIA)]
        d_gb = distances[(Species.GERANIUM, Species.BEGONIA)]

        if d_rg <= 0 or d_rb <= 0 or d_gb <= 0:
            return None

        x_b = (d_rb**2 + d_rg**2 - d_gb**2) / (2 * d_rg)
        y_sq = max(d_rb**2 - x_b**2, 0.0)
        y_b = math.sqrt(y_sq)

        positions = {
            Species.RHODODENDRON: (0.0, 0.0),
            Species.GERANIUM: (d_rg, 0.0),
            Species.BEGONIA: (x_b, y_b),
        }
        return positions

    def _build_layout(
        self,
        r_var: PlantVariety,
        g_var: PlantVariety,
        b_var: PlantVariety,
    ) -> (
        tuple[
            dict[Species, tuple[float, float]],
            float,
            dict[tuple[Species, Species], float],
        ]
        | None
    ):
        distances = self._compute_triangle_distances(r_var, g_var, b_var)
        if distances is None:
            return None

        positions = self._solve_triangle_geometry(distances)
        if positions is None:
            return None

        cx = sum(pt[0] for pt in positions.values()) / 3.0
        cy = sum(pt[1] for pt in positions.values()) / 3.0

        relative = {species: (pt[0] - cx, pt[1] - cy) for species, pt in positions.items()}

        radius_map = {
            Species.RHODODENDRON: self._get_radius(r_var),
            Species.GERANIUM: self._get_radius(g_var),
            Species.BEGONIA: self._get_radius(b_var),
        }
        cluster_extent = max(
            math.hypot(dx, dy) + radius_map[species] for species, (dx, dy) in relative.items()
        )

        return relative, cluster_extent + 0.25, distances

    def _simulate_triplet(
        self,
        r_var: PlantVariety,
        g_var: PlantVariety,
        b_var: PlantVariety,
        layout: tuple[
            dict[Species, tuple[float, float]], float, dict[tuple[Species, Species], float]
        ],
        key: tuple[tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]],
    ) -> TripletStrategy._TripletEval | None:
        relative, cluster_extent, distances = layout

        garden = Garden(width=20.0, height=20.0)
        anchor_x, anchor_y = 10.0, 10.0
        mapping = {
            Species.RHODODENDRON: r_var,
            Species.GERANIUM: g_var,
            Species.BEGONIA: b_var,
        }

        plants: dict[Species, Any] = {}
        for species, variety in mapping.items():
            dx, dy = relative[species]
            pos = Position(anchor_x + dx, anchor_y + dy)
            plant = garden.add_plant(variety, pos)
            if plant is None:
                return None
            plants[species] = plant

        engine = Engine(garden)
        per_turn_growth: list[float] = []
        for _ in range(400):
            growth = engine.run_turn()
            per_turn_growth.append(growth)
            if all(plant.is_fully_grown() for plant in garden.plants):
                break

        total_growth = sum(plant.size for plant in garden.plants)
        per_species_growth = {species: plants[species].size for species in mapping}
        recent_growth = sum(per_turn_growth[-30:]) if per_turn_growth else 0.0
        min_ratio = min(plants[species].size / plants[species].max_size for species in mapping)
        sustaining = min_ratio >= 0.5 or recent_growth > 0.5

        return self._TripletEval(
            key=key,
            total_growth=total_growth,
            per_species_growth=per_species_growth,
            sustaining=sustaining,
            relative_positions=relative,
            cluster_extent=cluster_extent,
            pair_distances=distances,
        )

    def _get_triplet_eval(
        self,
        r_type: TripletStrategy._VarType,
        g_type: TripletStrategy._VarType,
        b_type: TripletStrategy._VarType,
    ) -> TripletStrategy._TripletEval | None:
        cache_key = (r_type.key, g_type.key, b_type.key)
        if cache_key in self._triplet_cache:
            return self._triplet_cache[cache_key]

        layout = self._build_layout(r_type.prototype, g_type.prototype, b_type.prototype)
        if layout is None:
            return None

        evaluation = self._simulate_triplet(
            r_type.prototype,
            g_type.prototype,
            b_type.prototype,
            layout,
            cache_key,
        )
        if evaluation is not None:
            self._triplet_cache[cache_key] = evaluation
        return evaluation

    def _build_triplet_plans(
        self,
        by_species: dict[Species, list[TripletStrategy._VarType]],
    ) -> tuple[list[TripletStrategy._TripletPlan], float]:
        r_types = by_species.get(Species.RHODODENDRON, [])
        g_types = by_species.get(Species.GERANIUM, [])
        b_types = by_species.get(Species.BEGONIA, [])

        if not (r_types and g_types and b_types):
            return [], 0.0

        candidates: list[
            tuple[
                float,
                TripletStrategy._VarType,
                TripletStrategy._VarType,
                TripletStrategy._VarType,
                TripletStrategy._TripletEval,
            ]
        ] = []
        for r_type in r_types:
            for g_type in g_types:
                for b_type in b_types:
                    evaluation = self._get_triplet_eval(r_type, g_type, b_type)
                    if evaluation is None or not evaluation.sustaining:
                        continue
                    candidates.append((evaluation.total_growth, r_type, g_type, b_type, evaluation))

        candidates.sort(key=lambda item: item[0], reverse=True)

        plans: list[TripletStrategy._TripletPlan] = []
        cluster_extent = 0.0
        while True:
            chosen: (
                tuple[
                    TripletStrategy._VarType,
                    TripletStrategy._VarType,
                    TripletStrategy._VarType,
                    TripletStrategy._TripletEval,
                ]
                | None
            ) = None
            for _, r_type, g_type, b_type, evaluation in candidates:
                if r_type.available and g_type.available and b_type.available:
                    chosen = (r_type, g_type, b_type, evaluation)
                    break
            if chosen is None:
                break

            r_type, g_type, b_type, evaluation = chosen
            r_idx = r_type.reserve()
            g_idx = g_type.reserve()
            b_idx = b_type.reserve()
            if r_idx is None or g_idx is None or b_idx is None:
                break

            plans.append(
                self._TripletPlan(
                    r_type=r_type,
                    g_type=g_type,
                    b_type=b_type,
                    layout=evaluation,
                    indices={
                        Species.RHODODENDRON: r_idx,
                        Species.GERANIUM: g_idx,
                        Species.BEGONIA: b_idx,
                    },
                )
            )
            cluster_extent = max(cluster_extent, evaluation.cluster_extent)

        return plans, cluster_extent

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        self.garden = garden
        self.varieties = varieties
        seed = getattr(garden, 'seed', 42)
        self._rng = random.Random(seed)
        self._triplet_cache: dict[
            tuple[tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]],
            TripletStrategy._TripletEval,
        ] = {}

    def cultivate(self) -> None:
        if not self.varieties:
            return

        rng = self._rng
        width, height = float(self.garden.width), float(self.garden.height)

        by_species = self._build_type_groups(rng)
        triplet_plans, cluster_extent = self._build_triplet_plans(by_species)

        min_r = min((self._get_radius(v) for v in self.varieties), default=1.0)
        space = self._SpatialHash(
            cell_size=min_r * 0.75,
            width=width,
            height=height,
            get_radius=self._get_radius,
            get_species=self._get_species_enum,
        )

        placements: list[TripletStrategy._Placement] = []
        placed: list[bool] = [False] * len(self.varieties)

        if cluster_extent <= 0.0:
            cluster_extent = max(self._get_radius(v) for v in self.varieties) + 0.5

        anchor_spacing = max(cluster_extent * 1.8, min(width, height) / 6.0)
        anchors = self._tri_lattice(width, height, anchor_spacing)
        rng.shuffle(anchors)
        anchor_idx = 0

        for plan in triplet_plans:
            success = False
            while anchor_idx < len(anchors):
                anchor = anchors[anchor_idx]
                anchor_idx += 1
                if self._place_triplet_plan(
                    plan,
                    anchor,
                    space,
                    placements,
                    placed,
                    width,
                    height,
                    rng,
                ):
                    success = True
                    break
            if not success:
                for _ in range(40):
                    anchor = (rng.uniform(0.0, width), rng.uniform(0.0, height))
                    if self._place_triplet_plan(
                        plan,
                        anchor,
                        space,
                        placements,
                        placed,
                        width,
                        height,
                        rng,
                    ):
                        success = True
                        break

        for idx in range(len(self.varieties)):
            if placed[idx]:
                continue
            self._place_single(idx, space, placements, placed, width, height, rng)

    # ---------------------------
    # Small geometry helpers
    # ---------------------------

    @staticmethod
    def _rotate_point(x: float, y: float, angle: float) -> tuple[float, float]:
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

    def _place_triplet_plan(
        self,
        plan: TripletStrategy._TripletPlan,
        anchor: tuple[float, float],
        space: _SpatialHash,
        placements: list[TripletStrategy._Placement],
        placed: list[bool],
        width: float,
        height: float,
        rng: random.Random,
    ) -> bool:
        anchor_x, anchor_y = anchor
        jitter_scale = min(0.4, max(0.1, plan.layout.cluster_extent * 0.05))
        base_angles = [0.0, math.pi / 3, 2 * math.pi / 3, math.pi, 4 * math.pi / 3, 5 * math.pi / 3]
        angles = base_angles + [rng.uniform(0.0, 2 * math.pi)]

        for angle in angles:
            shift_x = rng.uniform(-jitter_scale, jitter_scale)
            shift_y = rng.uniform(-jitter_scale, jitter_scale)

            coords: dict[Species, tuple[float, float]] = {}
            valid = True
            for species, rel in plan.layout.relative_positions.items():
                rx, ry = self._rotate_point(rel[0], rel[1], angle)
                x = anchor_x + shift_x + rx
                y = anchor_y + shift_y + ry
                if not (0.0 <= x <= width and 0.0 <= y <= height):
                    valid = False
                    break
                coords[species] = (x, y)
            if not valid or len(coords) < 3:
                continue

            temp: list[TripletStrategy._Placement] = []
            feasible = True
            for species in (Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA):
                idx = plan.indices[species]
                if placed[idx]:
                    feasible = False
                    break
                x, y = coords[species]
                cand = self._Placement(idx, x, y)
                if not space.can_place(
                    cand,
                    self.varieties,
                    extras=temp,
                    allow_cross_existing=False,
                    allow_cross_extras=True,
                ):
                    feasible = False
                    break
                temp.append(cand)

            if not feasible:
                continue

            for cand in temp:
                plant = self.garden.add_plant(self.varieties[cand.idx], Position(cand.x, cand.y))
                if plant is None:
                    return False
                space.add(cand)
                placements.append(cand)
                placed[cand.idx] = True
            return True

        return False

    def _place_single(
        self,
        idx: int,
        space: _SpatialHash,
        placements: list[TripletStrategy._Placement],
        placed: list[bool],
        width: float,
        height: float,
        rng: random.Random,
    ) -> bool:
        if placed[idx]:
            return True

        attempts = 0
        while attempts < 1200:
            attempts += 1
            x = rng.uniform(0.0, width)
            y = rng.uniform(0.0, height)
            cand = self._Placement(idx, x, y)
            if not space.can_place(cand, self.varieties, allow_cross_existing=False):
                continue
            plant = self.garden.add_plant(self.varieties[idx], Position(x, y))
            if plant is None:
                continue
            space.add(cand)
            placements.append(cand)
            placed[idx] = True
            return True
        return False

    @staticmethod
    def _tri_lattice(width: float, height: float, spacing: float) -> list[tuple[float, float]]:
        """Generate a triangular (hex) lattice covering the rectangle."""
        pts: list[tuple[float, float]] = []
        row_h = spacing * math.sqrt(3) / 2.0
        rows = int(math.ceil(height / row_h)) + 2
        cols = int(math.ceil(width / spacing)) + 2
        for r in range(rows):
            y = r * row_h
            if y > height:
                break
            x_offset = 0.0 if (r % 2 == 0) else (spacing * 0.5)
            for c in range(cols):
                x = x_offset + c * spacing
                if x > width:
                    break
                pts.append((x, y))
        return pts
