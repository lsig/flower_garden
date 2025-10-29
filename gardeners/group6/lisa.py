"""Force-directed layout algorithm for optimal plant placement with structured seeding
and aggressive, size-aware placement to maximize successful plant count.
"""

import random
from typing import List, Tuple
import math

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.point import Position

# Optional tqdm import for progress bars
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, desc=None, leave=None):
        return iterable

from gardeners.group6.algorithms import (
    create_beneficial_interactions,
    measure_garden_quality,
    scatter_seeds_randomly,
    separate_overlapping_plants,
)


class Gardener6(Gardener):
    def __init__(self, garden: Garden, varieties: List[PlantVariety]):
        super().__init__(garden, varieties)

        # -------- Capacity & scaling --------
        num_plants = len(varieties)

        # Configurable cap (OFF by default) — set to True to re-enable the old 50 cap.
        self.enforce_variety_cap = False
        if self.enforce_variety_cap and num_plants > 50:
            random.shuffle(varieties)
            self.varieties = varieties[:50]
            num_plants = 50

        scale_factor = max(1, num_plants // 10)  # 1 for ≤10, 2 for ≤20, 5 for ≤50
        self.num_seeds = max(3, 18 // scale_factor)
        self.feasible_iters = max(40, 300 // scale_factor)
        self.nutrient_iters = max(75, 420 // scale_factor)

        # Force parameters
        self.band_delta = 0.25
        self.degree_cap = 5
        self.top_k_simulate = 1
        self.step_size_feasible = 0.18
        self.step_size_nutrient = 0.0002

        # Optional radius-based refinement
        self.enable_radius_refinement = True
        self.refine_iters = max(50, 300 // scale_factor)
        self.refine_step = 0.08
        self.inner_margin = 0.18
        self.outer_margin = 0.06

        # -------- Structured seeding controls --------
        self.center_small_fraction = 0.40
        self.edge_band_thickness = 0.12
        self.diamond_radius_fraction = 0.28
        self.target_jitter = 0.015

        # -------- Placement maximization settings --------
        # Spiral/jitter search around a target if add_plant fails
        self.place_retry_attempts = 80
        self.place_retry_growth = 1.15  # radial growth per ring
        self.place_retry_start = 0.5    # start radius multiplier of plant radius
        # Final recovery sweep attempts per remaining plant
        self.recovery_attempts = 120

    # ------------------ Main entry ------------------

    def cultivate_garden(self) -> None:
        """Place plants using structured seeding + force-directed polishing."""
        if not self.varieties:
            return

        best_score = -float('inf')
        best_layout = None
        best_labels = None

        # Allow more candidate points for denser packing
        target_plants = min(len(self.varieties) * 10, 640)

        for _ in tqdm(range(self.num_seeds), desc='Multi-start optimization', leave=True):
            # Random scatter to get labels / inv; we overwrite positions after
            X, labels, inv = scatter_seeds_randomly(
                self.varieties,
                W=self.garden.width,
                H=self.garden.height,
                target_count=target_plants,
            )

            # Impose the diamond/edge structured seed
            X = self._impose_center_diamond_and_edge_band(X, labels)

            # Let nutrients attract (soft), not enforcing feasibility yet
            X = create_beneficial_interactions(
                X,
                self.varieties,
                labels,
                inv,
                iters=self.nutrient_iters,
                band_delta=self.band_delta,
                degree_cap=self.degree_cap,
                step_size=self.step_size_nutrient,
                keep_feasible=False,
            )

            # Enforce non-overlap / hard constraints
            X = separate_overlapping_plants(
                X,
                self.varieties,
                labels,
                iters=self.feasible_iters,
                step_size=self.step_size_feasible,
            )

            # Optional gentle size-based refinement
            if self.enable_radius_refinement:
                X = self._iterative_radius_layout_refinement(
                    X,
                    labels,
                    iters=self.refine_iters,
                    step=self.refine_step,
                    inner_margin=self.inner_margin,
                    outer_margin=self.outer_margin,
                )

            score = measure_garden_quality(X, self.varieties, labels)
            if score > best_score:
                best_score = score
                best_layout = [pos for pos in X]
                best_labels = labels.copy()

        # Place the best layout we found (with aggressive retries & recovery)
        if best_layout is not None:
            self._place_plants_maximizing_count(best_layout, best_labels)

    # ------------------ Structured seeding core ------------------

    def _impose_center_diamond_and_edge_band(
        self,
        X: List[Tuple[float, float]],
        labels: List[int],
    ) -> List[Tuple[float, float]]:
        if not X:
            return X

        W, H = self.garden.width, self.garden.height
        cx, cy = W / 2.0, H / 2.0
        m = min(W, H)

        radii = [self.varieties[lbl].radius for lbl in labels]
        idx_sorted_small_to_large = sorted(range(len(labels)), key=lambda i: radii[i])

        n = len(labels)
        n_center = max(1, int(self.center_small_fraction * n))
        center_ids = idx_sorted_small_to_large[:n_center]
        edge_ids   = idx_sorted_small_to_large[-n_center:]
        middle_ids = [i for i in range(n) if i not in center_ids and i not in edge_ids]

        diamond_radius = self.diamond_radius_fraction * m

        center_targets = self._diamond_quadrant_targets(
            count=n_center,
            cx=cx, cy=cy,
            radius=diamond_radius,
            jitter=self.target_jitter * m
        )
        edge_targets = self._edge_band_targets(
            count=len(edge_ids),
            W=W, H=H,
            band=self.edge_band_thickness * m,
            jitter=self.target_jitter * m
        )
        middle_targets = self._annulus_targets_between_diamond_and_edge(
            count=len(middle_ids),
            cx=cx, cy=cy,
            W=W, H=H,
            inner=diamond_radius * 1.05,
            outer=(m / 2.0) - (self.edge_band_thickness * m) * 1.25,
            jitter=self.target_jitter * m
        )

        for k, i in enumerate(center_ids):
            X[i] = center_targets[k]
        for k, i in enumerate(edge_ids):
            X[i] = edge_targets[k]
        for k, i in enumerate(middle_ids):
            X[i] = middle_targets[k]
        return X

    # ---------- Target generation helpers ----------

    def _diamond_quadrant_targets(
        self, count: int, cx: float, cy: float, radius: float, jitter: float
    ) -> List[Tuple[float, float]]:
        if count <= 0:
            return []
        pts: List[Tuple[float, float]] = []
        per_quad = [count // 4] * 4
        for r in range(count % 4):
            per_quad[r] += 1

        def tri_sample(n, p0, p1, p2):
            out = []
            for _ in range(n):
                t = random.random()
                u = random.random() * (1.0 - t)
                x = p0[0] + t * (p1[0] - p0[0]) + u * (p2[0] - p0[0])
                y = p0[1] + t * (p1[1] - p0[1]) + u * (p2[1] - p0[1])
                x += (random.random() - 0.5) * 2 * jitter
                y += (random.random() - 0.5) * 2 * jitter
                out.append((x, y))
            return out

        top    = (cx, cy - radius)
        right  = (cx + radius, cy)
        bottom = (cx, cy + radius)
        left   = (cx - radius, cy)

        pts += tri_sample(per_quad[0], (cx, cy), top, right)
        pts += tri_sample(per_quad[1], (cx, cy), right, bottom)
        pts += tri_sample(per_quad[2], (cx, cy), bottom, left)
        pts += tri_sample(per_quad[3], (cx, cy), left, top)

        return [self._clamp_to_diamond(p, cx, cy, radius) for p in pts]

    def _edge_band_targets(
        self, count: int, W: float, H: float, band: float, jitter: float
    ) -> List[Tuple[float, float]]:
        if count <= 0:
            return []
        edges = ['top', 'right', 'bottom', 'left']
        pts: List[Tuple[float, float]] = []
        for i in range(count):
            edge = edges[i % 4]
            if edge == 'top':
                x = random.uniform(band, W - band); y = band
            elif edge == 'right':
                x = W - band; y = random.uniform(band, H - band)
            elif edge == 'bottom':
                x = random.uniform(band, W - band); y = H - band
            else:
                x = band; y = random.uniform(band, H - band)
            x += (random.random() - 0.5) * 2 * jitter
            y += (random.random() - 0.5) * 2 * jitter
            pts.append((self._clamp(x, 0, W), self._clamp(y, 0, H)))
        return pts

    def _annulus_targets_between_diamond_and_edge(
        self, count: int, cx: float, cy: float, W: float, H: float,
        inner: float, outer: float, jitter: float
    ) -> List[Tuple[float, float]]:
        if count <= 0:
            return []
        pts: List[Tuple[float, float]] = []
        for _ in range(count):
            theta = random.random() * 2 * math.pi
            r = random.uniform(inner, max(inner, outer))
            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)
            x += (random.random() - 0.5) * 2 * jitter
            y += (random.random() - 0.5) * 2 * jitter
            pts.append((self._clamp(x, 0, W), self._clamp(y, 0, H)))
        return pts

    # ---------- Geometry helpers ----------

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    @staticmethod
    def _clamp_to_diamond(p: Tuple[float, float], cx: float, cy: float, a: float) -> Tuple[float, float]:
        x, y = p
        dx, dy = abs(x - cx), abs(y - cy)
        s = dx / a + dy / a
        if s <= 1.0 or a <= 0:
            return x, y
        if dx + dy == 0:
            return cx, cy
        k = a / (dx + dy)  # project onto |dx|+|dy|=a
        nx = cx + (x - cx) * k
        ny = cy + (y - cy) * k
        return nx, ny

    # ------------------ Optional refinement ------------------

    def _iterative_radius_layout_refinement(
        self,
        X: List[Tuple[float, float]],
        labels: List[int],
        iters: int = 100,
        step: float = 0.08,
        inner_margin: float = 0.18,
        outer_margin: float = 0.06,
        tol: float = 1e-3,
    ) -> List[Tuple[float, float]]:
        if not X:
            return X
        W, H = self.garden.width, self.garden.height
        cx, cy = W / 2.0, H / 2.0
        garden_half = min(W, H) / 2.0

        radii = [self.varieties[lbl].radius for lbl in labels]
        r_min = min(radii); r_max = max(radii)
        r_span = (r_max - r_min) if (r_max > r_min) else 1.0

        target_inner = garden_half * inner_margin
        target_outer = garden_half * (1.0 - outer_margin)

        Xw = [list(p) for p in X]
        for _ in range(iters):
            max_shift = 0.0
            for i, (x, y) in enumerate(Xw):
                r_norm = (radii[i] - r_min) / r_span
                target = target_inner + (target_outer - target_inner) * r_norm
                dx, dy = x - cx, y - cy
                dist = (dx * dx + dy * dy) ** 0.5 or 1e-6
                ux, uy = dx / dist, dy / dist
                delta = target - dist
                move = step * delta
                nx = self._clamp(cx + ux * (dist + move), 0.0, W)
                ny = self._clamp(cy + uy * (dist + move), 0.0, H)
                max_shift = max(max_shift, abs(move))
                Xw[i][0], Xw[i][1] = nx, ny
            if max_shift < tol:
                break
        return [(p[0], p[1]) for p in Xw]

    # ------------------ Placement (maximize count) ------------------

    def _place_plants_maximizing_count(self, X: List[Tuple[float, float]], labels: List[int]) -> None:
        """
        Place plants with:
          1) Big-first ordering to preserve space.
          2) Local spiral/jitter retry if a placement fails.
          3) Recovery sweep for any unplaced plants using size-aware fallback targets.
        """
        n = len(labels)
        W, H = self.garden.width, self.garden.height
        cx, cy = W / 2.0, H / 2.0
        m = min(W, H)
        diamond_radius = self.diamond_radius_fraction * m

        radii = [self.varieties[lbl].radius for lbl in labels]
        order = sorted(range(n), key=lambda i: radii[i], reverse=True)  # big first

        failed_indices: List[int] = []

        # First pass: try original targets with backoff
        for idx in order:
            lbl = labels[idx]
            variety = self.varieties[lbl]
            target = X[idx]
            if not self._try_place_with_backoff(variety, target):
                failed_indices.append(idx)

        if not failed_indices:
            return  # everything placed

        # Prepare fallback target generators
        # Split remaining into small/middle/large again (relative to all radii)
        r_sorted = sorted([(i, radii[i]) for i in failed_indices], key=lambda t: t[1])
        k = len(r_sorted) // 3 or 1
        small_idxs = [i for i, _ in r_sorted[:k]]
        large_idxs = [i for i, _ in r_sorted[-k:]]
        middle_idxs = [i for i, _ in r_sorted if i not in small_idxs and i not in large_idxs]

        # Build new fallback targets
        small_targets = self._diamond_quadrant_targets(
            count=len(small_idxs),
            cx=cx, cy=cy,
            radius=diamond_radius,
            jitter=self.target_jitter * m
        )
        large_targets = self._edge_band_targets(
            count=len(large_idxs),
            W=W, H=H,
            band=self.edge_band_thickness * m,
            jitter=self.target_jitter * m
        )
        middle_targets = self._annulus_targets_between_diamond_and_edge(
            count=len(middle_idxs),
            cx=cx, cy=cy,
            W=W, H=H,
            inner=diamond_radius * 1.05,
            outer=(m / 2.0) - (self.edge_band_thickness * m) * 1.25,
            jitter=self.target_jitter * m
        )

        # Second pass: try fallback targets with more retries
        for i, tgt in zip(small_idxs, small_targets):
            lbl = labels[i]; variety = self.varieties[lbl]
            self._try_place_with_backoff(variety, tgt, attempts=self.recovery_attempts)

        for i, tgt in zip(large_idxs, large_targets):
            lbl = labels[i]; variety = self.varieties[lbl]
            self._try_place_with_backoff(variety, tgt, attempts=self.recovery_attempts)

        for i, tgt in zip(middle_idxs, middle_targets):
            lbl = labels[i]; variety = self.varieties[lbl]
            self._try_place_with_backoff(variety, tgt, attempts=self.recovery_attempts)

    def _try_place_with_backoff(
        self,
        variety: PlantVariety,
        target_xy: Tuple[float, float],
        attempts: int = None,
    ) -> bool:
        """
        Try to place a plant at (or near) target_xy. If add_plant fails, we
        spiral/jitter outward with a radius that grows relative to plant size.
        Returns True if placed, False otherwise.
        """
        if attempts is None:
            attempts = self.place_retry_attempts

        W, H = self.garden.width, self.garden.height
        base_r = getattr(variety, "radius", 1.0)
        radius = max(0.1, float(base_r))
        # Start with a small search radius and grow it multiplicatively
        search_r = max(0.2, self.place_retry_start * radius)

        cx, cy = target_xy
        for i in range(attempts):
            if i == 0:
                x, y = cx, cy
            else:
                angle = random.random() * 2 * math.pi
                # ring grows gradually; within ring, choose random point
                ring = search_r * (self.place_retry_growth ** (i / 6.0))
                dist = random.uniform(0.0, ring)
                x = cx + dist * math.cos(angle)
                y = cy + dist * math.sin(angle)

            # clamp to garden bounds
            x = self._clamp(x, 0.0, W)
            y = self._clamp(y, 0.0, H)

            pos = Position(x=x, y=y)
            try:
                ok = self.garden.add_plant(variety, pos)
            except Exception:
                # Some implementations raise on invalid; treat as failure and continue
                ok = False

            if ok or ok is None:
                # Convention: some add_plant() don't return bool; assume success if no exception
                return True

        return False

    # ------------------ Final placement API (legacy) ------------------

    def _place_plants(self, X: List[Tuple[float, float]], labels: List[int]) -> None:
        """Legacy simple placement (unused now)."""
        for i, label in enumerate(labels):
            variety = self.varieties[label]
            position = Position(x=X[i][0], y=X[i][1])
            self.garden.add_plant(variety, position)
