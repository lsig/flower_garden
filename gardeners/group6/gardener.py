# gardeners/group6/gardener.py
"""
Gardener6 — Hex Packer with Time Budgets & Spatial Hash (fast & robust)

- Hexagonal anchor grid (center-out).
- Greedy triads for balanced groups (O(n), not exponential).
- Time budgets: global + per-plant; prints when trimming search to meet time.
- Spatial hash to score/check only local neighbors (fast).
- Throttled candidate evaluation per plant to avoid timeouts.
- Multi-phase refills preserved, but budget-aware.

This file is self-contained; no imports from old group algorithms.
"""

from __future__ import annotations

import math
import random
import time

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.point import Position


class SpatialHash:
    """Tiny grid index for fast neighbor queries."""

    def __init__(self, cell: float):
        self.cell = max(1e-6, float(cell))
        self.buckets: dict[tuple[int, int], list[tuple[str, float, float, float]]] = {}

    def _key(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell), int(y // self.cell))

    def insert(self, species: str, x: float, y: float, r: float) -> None:
        k = self._key(x, y)
        self.buckets.setdefault(k, []).append((species, x, y, r))

    def nearby(self, x: float, y: float, radius: float) -> list[tuple[str, float, float, float]]:
        """Return plants in 3x3 cells around (x,y)."""
        cx, cy = self._key(x, y)
        out: list[tuple[str, float, float, float]] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.extend(self.buckets.get((cx + dx, cy + dy), []))
        return out


class Gardener6(Gardener):
    # ---------------- Tunables (speed & quality) ----------------
    EDGE_MARGIN_FRAC = 0.015  # 0.010
    STEP_FACTOR_MINR = 0.667  # 0.95          # hex step = factor * min_r
    GROUP_SIZE = 3  # triads
    MICRO_JITTER_TRIES = 4  # keep small for speed
    MICRO_JITTER_SCALE = 0.28  # 0.28
    MAX_CANDIDATES_PER_PLANT = 100  # 60         # hard cap per variety
    MULTI_PHASE_REFILLS = True
    SEED = None

    # Time budgets (seconds)
    GLOBAL_TIME_BUDGET_S = 5.0  # total time allowed in cultivate_garden
    PER_PLANT_BUDGET_MS = 15.0  # max ms to search anchors for one plant

    # Rules
    FORBID_SAME_SPECIES_OVERLAP = True

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.W, self.H = self.garden.width, self.garden.height
        self.margin = self.EDGE_MARGIN_FRAC * min(self.W, self.H)
        self.radii = [max(0.1, float(getattr(v, 'radius', 1.0))) for v in self.varieties]
        self.min_r = min(self.radii) if self.radii else 1.0
        if self.SEED is not None:
            random.seed(self.SEED)

        # spatial hash for already placed
        self.shash = SpatialHash(cell=self.min_r)

    # ---------------- Main ----------------

    def cultivate_garden(self) -> None:
        if not self.varieties:
            print('[DEBUG] No varieties; exiting.')
            return

        t0 = time.time()
        print(
            f'[DEBUG] Start with {len(self.varieties)} varieties; budget {self.GLOBAL_TIME_BUDGET_S:.1f}s'
        )

        step = max(0.2, self.STEP_FACTOR_MINR * self.min_r)
        base_grid = self._hex_grid(step)
        print(f'[DEBUG] Hex anchors: {len(base_grid)} (step={step:.3f})')

        # Greedy triads (fast grouping)
        groups = self._greedy_triads()
        print(f'[DEBUG] Greedy groups formed: {len(groups)} triads (size<=3)')

        used_anchor = set()
        placed_before = self._placed_count()

        # Place groups first (better growth), time-aware
        for gi, group in enumerate(groups, 1):
            if self._time_up(t0):
                print('[DEBUG] Time budget hit during groups; continuing with refills.')
                break
            self._place_group_fast(group, base_grid, used_anchor, t0)
            now = self._placed_count()
            if gi % 10 == 0:
                print(f'[DEBUG] Groups {gi}/{len(groups)} — placed +{now - placed_before}')
                placed_before = now

        # Leftovers (anything not yet planted)
        leftovers = [v for v in self.varieties if not self._in_garden(v)]
        print(f'[DEBUG] Leftovers after groups: {len(leftovers)}')

        # Refill passes (multi-phase), time-aware
        if leftovers and not self._time_up(t0):
            grids = [base_grid]
            if self.MULTI_PHASE_REFILLS:
                grids += self._hex_grid_multiphase(step)
                print(f'[DEBUG] Refill grids: {len(grids)}')

            for gi, grid in enumerate(grids, 1):
                if self._time_up(t0):
                    print('[DEBUG] Time budget hit during refills.')
                    break
                added = 0
                for v in list(leftovers):
                    if self._time_up(t0):
                        break
                    if self._place_one_fast(v, grid, t0):
                        leftovers.remove(v)
                        added += 1
                print(
                    f'[DEBUG] Refill {gi}/{len(grids)} placed {added}; remaining {len(leftovers)}'
                )
                if not leftovers:
                    break

        # Tight final pass if time remains
        if leftovers and not self._time_up(t0):
            tight_step = max(0.15, 0.88 * step)
            tight_grid = self._hex_grid(tight_step)
            random.shuffle(tight_grid)
            added = 0
            for v in list(leftovers):
                if self._time_up(t0):
                    break
                if self._place_one_fast(v, tight_grid, t0):
                    leftovers.remove(v)
                    added += 1
            print(f'[DEBUG] Tight pass placed {added}; remaining {len(leftovers)}')

        print(
            f'[DEBUG] Done. Planted={self._placed_count()}  Unplaced={len(leftovers)}  Elapsed={time.time() - t0:.2f}s'
        )

    # ---------------- Fast placement pieces ----------------

    def _place_group_fast(
        self, group: list[PlantVariety], grid: list[Position], used_anchor: set, t0: float
    ) -> None:
        """Place up to 3 plants, larger-first, evaluating limited anchors w/ time budget."""
        group_sorted = sorted(group, key=lambda v: getattr(v, 'radius', 1.0), reverse=True)
        for v in group_sorted:
            if self._time_up(t0):
                return
            self._place_one_fast(v, grid, t0, used_anchor)

    def _place_one_fast(
        self, v: PlantVariety, grid: list[Position], t0: float, used_anchor: set | None = None
    ) -> bool:
        """Try to place one plant scanning at most MAX_CANDIDATES_PER_PLANT anchors."""
        ms_budget = self.PER_PLANT_BUDGET_MS / 1000.0
        start = time.time()
        r = max(0.1, float(getattr(v, 'radius', 1.0)))

        # Iterate center-out, but limited; skip anchors we’ve “consumed”
        tried = 0
        best_pos = None
        best_score = -1e9

        for pos in grid:
            if self._time_up(t0):
                break
            if time.time() - start > ms_budget:
                break
            if tried >= self.MAX_CANDIDATES_PER_PLANT:
                break

            k = (round(pos.x, 3), round(pos.y, 3))
            if used_anchor and k in used_anchor:
                continue

            # quick same-species feasibility via shash
            if self.FORBID_SAME_SPECIES_OVERLAP and not self._same_species_ok(v, pos.x, pos.y, r):
                continue

            # cheap precheck
            if hasattr(self.garden, 'can_place_plant'):
                try:
                    if not self.garden.can_place_plant(v, pos):
                        tried += 1
                        continue
                except Exception:
                    pass

            # score = #cross-species neighbors overlap (local only) - small edge penalty
            score = self._local_overlaps_cross_species(v, pos.x, pos.y, r) - 0.02 * (
                abs(pos.x - self.W / 2.0) + abs(pos.y - self.H / 2.0)
            )
            if score > best_score:
                best_score = score
                best_pos = pos

            tried += 1

        if best_pos and self._add_with_jitter(v, best_pos, r):
            if used_anchor is not None:
                used_anchor.add((round(best_pos.x, 3), round(best_pos.y, 3)))
            return True

        # as a fallback: try immediate anchors sequentially until budget hits
        for pos in grid:
            if self._time_up(t0):
                break
            if time.time() - start > ms_budget:
                break
            if used_anchor and (round(pos.x, 3), round(pos.y, 3)) in used_anchor:
                continue
            if self.FORBID_SAME_SPECIES_OVERLAP and not self._same_species_ok(v, pos.x, pos.y, r):
                continue
            if hasattr(self.garden, 'can_place_plant'):
                try:
                    if not self.garden.can_place_plant(v, pos):
                        continue
                except Exception:
                    pass
            if self._add_with_jitter(v, pos, r):
                if used_anchor is not None:
                    used_anchor.add((round(pos.x, 3), round(pos.y, 3)))
                return True

        return False

    def _add_with_jitter(self, v: PlantVariety, pos: Position, r: float) -> bool:
        # direct
        if self._try_add(v, pos.x, pos.y, r):
            return True
        # micro jitters
        for _ in range(self.MICRO_JITTER_TRIES):
            ang = random.random() * 2 * math.pi
            d = random.uniform(0.0, self.MICRO_JITTER_SCALE * r)
            px = self._clamp(pos.x + d * math.cos(ang), 0.0, self.W)
            py = self._clamp(pos.y + d * math.sin(ang), 0.0, self.H)
            if self._try_add(v, px, py, r):
                return True
        # (no spiral here to keep it fast)
        return False

    # ---------------- Scoring & feasibility (fast, local) ----------------

    def _same_species_ok(self, v: PlantVariety, x: float, y: float, r: float) -> bool:
        """Reject if same-species neighbor would overlap; checks only local cells."""
        my_s = self._species_code(v)
        for s, px, py, pr in self.shash.nearby(x, y, r + self.min_r):
            if s != my_s:
                continue
            dx, dy = x - px, y - py
            if dx * dx + dy * dy < (r + pr) ** 2:
                return False
        return True

    def _local_overlaps_cross_species(self, v: PlantVariety, x: float, y: float, r: float) -> float:
        """Count overlapping roots with other species in neighboring cells only."""
        my_s = self._species_code(v)
        count = 0
        for s, px, py, pr in self.shash.nearby(x, y, r + self.min_r):
            if s == my_s:
                continue
            dx, dy = x - px, y - py
            if dx * dx + dy * dy < (r + pr) ** 2:
                count += 1
        return float(count)

    def _try_add(self, v: PlantVariety, x: float, y: float, r: float) -> bool:
        try:
            ok = self.garden.add_plant(v, Position(x, y))
        except Exception:
            ok = False
        if ok or ok is None:
            s = self._species_code(v)
            self.shash.insert(s, x, y, r)
            return True
        return False

    # ---------------- Hex grids ----------------

    def _hex_grid(self, spacing: float) -> list[Position]:
        positions: list[Position] = []
        dx = spacing
        dy = spacing * math.sqrt(3) / 2.0
        # center-out order
        y = self.margin
        row = 0
        while y <= self.H - self.margin:
            x_off = (dx / 2.0) if (row % 2) else 0.0
            x = self.margin + x_off
            while x <= self.W - self.margin:
                positions.append(Position(x, y))
                x += dx
            y += dy
            row += 1
        positions.sort(key=lambda p: abs(p.x - self.W / 2.0) + abs(p.y - self.H / 2.0))
        return positions

    def _hex_grid_multiphase(self, spacing: float) -> list[list[Position]]:
        phases = [(0.00, 0.50), (0.50, 0.25), (0.50, 0.75), (0.25, 0.25), (0.75, 0.75)]
        dx = spacing
        dy = spacing * math.sqrt(3) / 2.0
        grids: list[list[Position]] = []
        for rp, cp in phases:
            grid: list[Position] = []
            y = self.margin + rp * dy
            row = 0
            while y <= self.H - self.margin:
                x_off = (dx / 2.0) if (row % 2) else 0.0
                x = self.margin + x_off + cp * dx
                while x <= self.W - self.margin:
                    grid.append(Position(x, y))
                    x += dx
                y += dy
                row += 1
            grid.sort(key=lambda p: abs(p.x - self.W / 2.0) + abs(p.y - self.H / 2.0))
            grids.append(grid)
        return grids

    # ---------------- Greedy groups (fast) ----------------

    def _greedy_triads(self) -> list[list[PlantVariety]]:
        """Form R/G/B-balanced groups quickly using signs of coefficients."""
        by_s: dict[str, list[PlantVariety]] = {'R': [], 'G': [], 'B': []}
        for v in self.varieties:
            by_s[self._species_code(v)].append(v)

        # small→big so we can pack more
        for s in by_s:
            by_s[s].sort(key=lambda v: getattr(v, 'radius', 1.0))

        groups: list[list[PlantVariety]] = []
        # exact triads first
        while all(by_s[s] for s in ('R', 'G', 'B')):
            groups.append([by_s['R'].pop(0), by_s['G'].pop(0), by_s['B'].pop(0)])

        # make pairs or singles with what’s left (still helpful)
        leftovers = by_s['R'] + by_s['G'] + by_s['B']
        leftovers.sort(key=lambda v: getattr(v, 'radius', 1.0))
        i = 0
        while i < len(leftovers):
            groups.append([leftovers[i]])
            i += 1
        return groups

    # ---------------- Helpers ----------------

    def _species_code(self, v: PlantVariety) -> str:
        """Classify by nutrient coefficient signs; fall back to name prefix."""
        try:
            R = float(v.nutrient_coefficients[Micronutrient.R])
            G = float(v.nutrient_coefficients[Micronutrient.G])
            B = float(v.nutrient_coefficients[Micronutrient.B])
            eps = 1e-12
            if eps < R and -eps > G and -eps > B:
                return 'R'
            if eps < G and -eps > R and -eps > B:
                return 'G'
            if eps < B and -eps > R and -eps > G:
                return 'B'
        except Exception:
            pass
        name = str(getattr(v, 'species', '') or getattr(v, 'name', '')).lower()
        if name.startswith('r'):
            return 'R'
        if name.startswith('g'):
            return 'G'
        if name.startswith('b'):
            return 'B'
        return random.choice(['R', 'G', 'B'])  # never collapse to one bucket

    def _placed_count(self) -> int:
        try:
            return len(getattr(self.garden, 'plants', []))
        except Exception:
            return 0

    def _in_garden(self, v: PlantVariety) -> bool:
        # If you track placements per-variety elsewhere, wire it; we keep simple here.
        return False

    def _time_up(self, t0: float) -> bool:
        return (time.time() - t0) >= self.GLOBAL_TIME_BUDGET_S

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))
