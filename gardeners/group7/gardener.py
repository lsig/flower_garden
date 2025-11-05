import math
from collections import defaultdict, deque

from core.gardener import Gardener
from core.plants.species import Species
from core.point import Position


class Gardener7(Gardener):
    """
    Total-growth oriented placement with interaction-graph analysis and refinement.

    Flow:
      1) Core RGB triangle at center (tight, non-violating).
      2) Species-balanced adaptive packing (R,G,B interleaving; bounded runtime).
      3) Build interaction graph over placed plants (edges are cross-species overlaps).
      4) Refinement: try to place leftover/failed plants as "bridges" near isolated nodes.
      5) Print debug stats before/after refinement.

    Notes:
      • We do not remove already-placed plants (no API assumed). Refinement places from the failed pool.
      • All search loops are strictly bounded to avoid stalls.
      • We locally track placements (variety + position) so we can compute the interaction graph.
    """

    # ---------- Tunables (safe defaults for 16x10 garden, radii 1..3) ----------
    _EPS = 0.2
    _TINY = 1e-3

    # Adaptive packer bounds
    _BASE_STEP_MIN = 0.8
    _MAX_PHASES = 3
    _MAX_RING_RADIUS_FACTOR = 1.1
    _PTS_PER_RING_MAX = 60
    _MAX_PLANT_ATTEMPTS = 3
    _MAX_SWEEPS_WITH_NO_PLACEMENT = 3

    # Refinement
    _MIN_NEIGHBORS_TARGET = 2  # aim for at least 2 cross-species neighbors
    _REFINE_CANDIDATE_RADIUS = 2.5  # radius around isolated node to search for bridge placement
    _REFINE_POINTS = 24  # angular granularity near isolated node
    _REFINE_MAX_PLANTS = 10  # cap number of bridge attempts total
    _REFINE_MAX_PER_NODE = 2  # cap attempts per isolated node

    def __init__(self, garden, varieties):
        super().__init__(garden, varieties)
        # Local record of placed plants as dicts: {"v": variety, "x": float, "y": float}
        self._placed = []

    # ---------- Scoring ----------
    def _cooperation_score(self, v):
        coeffs = v.nutrient_coefficients
        if len(coeffs) > 0 and not isinstance(next(iter(coeffs.keys())), str):
            coeffs = {k.name: val for k, val in coeffs.items()}
        R = coeffs.get('R', 0.0)
        G = coeffs.get('G', 0.0)
        B = coeffs.get('B', 0.0)
        best_surplus = abs(max(R, G, B))
        best_deficit = abs(min(R, G, B))
        return best_surplus / (best_deficit * pow(v.radius, 2))

    # ---------- Low-level helpers ----------
    def _add_and_track(self, v, x, y):
        """Try to add plant and record placement locally if successful."""
        if (
            0.0 < x < self.garden.width
            and 0.0 < y < self.garden.height
            and self.garden.add_plant(v, Position(x, y))
        ):
            self._placed.append({'v': v, 'x': x, 'y': y})
            return True

    def _safe_place(self, v, x, y):
        """Place with small jitters for last-mile fits, recording on success."""
        for dx in (0.0, 0.3, -0.3, 0.7, -0.7, 1.0, -1.0):
            for dy in (0.0, 0.3, -0.3, 0.7, -0.7, 1.0, -1.0):
                if self._add_and_track(v, x + dx, y + dy):
                    return True
        return False

    # ---------- Geometry ----------
    def _circle_intersection(self, x0, y0, r0, x1, y1, r1, choose_upper=True):
        dx = x1 - x0
        dy = y1 - y0
        d = math.hypot(dx, dy)
        if d < 1e-9:
            # arbitrary opposite points along +x/-x from (x0,y0)
            return (x0 + min(r0, r1), y0) if choose_upper else (x0 - min(r0, r1), y0)

        a = (r0 * r0 - r1 * r1 + d * d) / (2 * d)
        h_sq = max(0.0, r0 * r0 - a * a)
        h = math.sqrt(h_sq)

        xm = x0 + a * dx / d
        ym = y0 + a * dy / d
        rx = -dy * (h / d)
        ry = dx * (h / d)

        xi, yi = xm + rx, ym + ry
        xi2, yi2 = xm - rx, ym - ry
        if choose_upper:
            return (xi, yi) if yi >= yi2 else (xi2, yi2)
        else:
            return (xi, yi) if yi < yi2 else (xi2, yi2)

    # ---------- Candidate generation for adaptive packer ----------
    def _spiral_candidates(self, cx, cy, base_step):
        """Bounded outward ring scan around center."""
        diag = math.hypot(self.garden.width, self.garden.height)
        r = base_step
        limit = diag * self._MAX_RING_RADIUS_FACTOR
        while r < limit:
            pts = min(self._PTS_PER_RING_MAX, max(8, int(2 * math.pi * r / max(base_step, 0.2))))
            for i in range(pts):
                ang = 2 * math.pi * i / pts
                # >>> CHANGED: yield only in-bounds points
                x = cx + r * math.cos(ang)
                y = cy + r * math.sin(ang)
                if 0.0 < x < self.garden.width and 0.0 < y < self.garden.height:
                    yield (x, y)
                # <<< END CHANGE
            r += base_step

    # ---------- Balanced queue to avoid species monopolizing early slots ----------
    def _balanced_queue(self, reds, greens, blues):
        q = []
        groups = [deque(reds), deque(greens), deque(blues)]
        while any(groups):
            for g in groups:
                if g:
                    q.append(g.popleft())
        return q

    # ---------- Adaptive packer with bounded attempts; returns list of unplaced plants ----------
    def _pack_adaptive(self, queue, cx, cy):
        attempts = {id(v): self._MAX_PLANT_ATTEMPTS for v in queue}
        sweeps_without_progress = 0
        failed = []

        while queue and sweeps_without_progress < self._MAX_SWEEPS_WITH_NO_PLACEMENT:
            placed_any = False
            next_q = []

            for v in queue:
                if attempts[id(v)] <= 0:
                    failed.append(v)
                    continue

                placed = False
                base_step = max(self._BASE_STEP_MIN, v.radius * 0.7)

                # >>> CHANGED: choose a per-plant anchor near frontier (last cross-species)
                ax, ay = cx, cy
                if self._placed:
                    # find most recent cross-species placement to bias toward interaction
                    for p in reversed(self._placed):
                        if p['v'].species != v.species:
                            ax, ay = p['x'], p['y']
                            break
                # <<< END CHANGE

                for _ in range(self._MAX_PHASES):
                    # >>> CHANGED: spiral around (ax, ay) instead of always (cx, cy)
                    for x, y in self._spiral_candidates(ax, ay, base_step):
                        if self._safe_place(v, x, y):
                            placed = True
                            placed_any = True
                            break
                    # <<< END CHANGE
                    if placed:
                        break

                if not placed:
                    attempts[id(v)] -= 1
                    if attempts[id(v)] > 0:
                        next_q.append(v)
                    else:
                        failed.append(v)

            sweeps_without_progress = 0 if placed_any else sweeps_without_progress + 1
            queue = next_q

        # Anything left in queue after loops gets marked failed
        failed.extend(queue)
        return failed

    # ---------- Core RGB triangle ----------
    def _place_core_triangle(self, r, g, b, cx, cy):
        core = sorted([r, g, b], key=lambda v: v.radius, reverse=True)
        A, B, C = core
        self._add_and_track(A, cx, cy)

        eps = self._EPS
        AB = A.radius + B.radius - eps
        AC = A.radius + C.radius - eps

        # Place B on +x from center
        self._add_and_track(B, cx + max(AB, self._TINY), cy)

        # Place C roughly above-left using a safe distance
        xC, yC = self._circle_intersection(
            cx,
            cy,
            max(AC, self._TINY),
            cx + max(AB, self._TINY),
            cy,
            B.radius + C.radius - eps,
            choose_upper=True,
        )

        # gentle pull toward both A and B to tighten but not violate
        def pull(xa, ya, xb, yb, f):
            return xa + (xb - xa) * f, ya + (yb - ya) * f

        xC, yC = pull(xC, yC, cx, cy, 0.25)
        xC, yC = pull(xC, yC, cx + max(AB, self._TINY), cy, 0.25)
        self._safe_place(C, xC, yC)

    # ---------- Interaction graph ----------
    def _distance(self, i, j):
        pi, pj = self._placed[i], self._placed[j]
        dx = pi['x'] - pj['x']
        dy = pi['y'] - pj['y']
        return math.hypot(dx, dy)

    def _neighbors_cross_species(self, i):
        vi = self._placed[i]['v']
        ri = vi.radius
        si = vi.species
        neigh = []
        for j in range(len(self._placed)):
            if j == i:
                continue
            vj = self._placed[j]['v']
            if vj.species == si:
                continue
            rj = vj.radius
            if self._distance(i, j) < ri + rj:
                neigh.append(j)
        return neigh

    def _build_interaction_graph(self):
        adj = {i: set() for i in range(len(self._placed))}
        degs = []
        for i in range(len(self._placed)):
            nbrs = self._neighbors_cross_species(i)
            for j in nbrs:
                adj[i].add(j)
                adj[j].add(i)
        for i in range(len(self._placed)):
            degs.append(len(adj[i]))
        return adj, degs

    def _print_graph_stats(self, when_label):
        by_species = defaultdict(int)
        for p in self._placed:
            by_species[p['v'].species] += 1

        total = len(self._placed)
        r = by_species[Species.RHODODENDRON]
        g = by_species[Species.GERANIUM]
        b = by_species[Species.BEGONIA]

        adj, degs = self._build_interaction_graph()
        iso = sum(1 for d in degs if d == 0)
        leaves = sum(1 for d in degs if d == 1)
        avg_deg = (sum(degs) / total) if total else 0.0

        hist = defaultdict(int)
        for d in degs:
            hist[d] += 1
        hist_str = ' '.join(f'{k}:{v}' for k, v in sorted(hist.items()))

        print(f'[{when_label}] Placed={total} (R={r}, G={g}, B={b})')
        print(f'[{when_label}] Avg cross-species neighbors: {avg_deg:.2f}')
        print(f'[{when_label}] Isolated: {iso}, Leaves: {leaves}  | Degree hist: {hist_str}')

    # ---------- Refinement using failed pool as bridges ----------
    def _refine_with_failed_pool(self, failed):
        if not failed:
            print('[Refine] No failed plants available for bridging. Skipping.]')
            return

        adj, degs = self._build_interaction_graph()
        isolated_ids = [i for i, d in enumerate(degs) if d < self._MIN_NEIGHBORS_TARGET]

        if not isolated_ids:
            print('[Refine] No isolated/low-degree plants found. Skipping.')
            return

        # Sort failed pool by radius small->large to fit near isolated nodes,
        # and by cooperation score to pick helpful donors/receivers.
        failed.sort(key=lambda v: (v.radius, -self._cooperation_score(v)))

        successes = 0
        attempts_total = 0

        for iso_idx in isolated_ids:
            if successes >= self._REFINE_MAX_PLANTS:
                break
            # Target plant info
            pv = self._placed[iso_idx]['v']
            px = self._placed[iso_idx]['x']
            py = self._placed[iso_idx]['y']

            # Prefer a species different from the isolated plant
            def pop_preferred(target_species=pv.species):
                for s in (Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA):
                    if s == target_species:
                        continue
                    for k in range(len(failed)):
                        if failed[k].species == s:
                            return failed.pop(k)
                return failed.pop(0) if failed else None

            placed_here = 0
            for _ in range(self._REFINE_MAX_PER_NODE):
                if not failed or successes >= self._REFINE_MAX_PLANTS:
                    break
                cand = pop_preferred()
                if cand is None:
                    break

                attempts_total += 1

                # Try a ring of points around the isolated plant
                r = max(0.6, min(self._REFINE_CANDIDATE_RADIUS, cand.radius * 3.0))
                pts = self._REFINE_POINTS
                for i in range(pts):
                    ang = 2 * math.pi * i / pts
                    x = px + r * math.cos(ang)
                    y = py + r * math.sin(ang)
                    if self._safe_place(cand, x, y):
                        successes += 1
                        placed_here += 1
                        break

            if placed_here > 0:
                # Recompute to see if this node is now healthy
                adj, degs = self._build_interaction_graph()

        print(f'[Refine] Tried placing {attempts_total} bridge plants. Successes: {successes}')

    # ---------- Main ----------
    def cultivate_garden(self):
        self._placed = []  # reset local record for a fresh run

        # --- Select top ~50 per species + 1 best extra to cap at 151
        reds_all = [v for v in self.varieties if v.species == Species.RHODODENDRON]
        greens_all = [v for v in self.varieties if v.species == Species.GERANIUM]
        blues_all = [v for v in self.varieties if v.species == Species.BEGONIA]

        reds_all.sort(key=self._cooperation_score, reverse=True)
        greens_all.sort(key=self._cooperation_score, reverse=True)
        blues_all.sort(key=self._cooperation_score, reverse=True)

        base_cap = 50
        reds = reds_all[:base_cap]
        greens = greens_all[:base_cap]
        blues = blues_all[:base_cap]

        # pick one extra (best next-available across species) to reach 187 if possible
        extras = []
        if len(reds_all) > base_cap:
            extras.append(reds_all[base_cap])
        if len(greens_all) > base_cap:
            extras.append(greens_all[base_cap])
        if len(blues_all) > base_cap:
            extras.append(blues_all[base_cap])
        if extras:
            extras.sort(key=self._cooperation_score, reverse=True)
            extra = extras[0]
            if extra.species == Species.RHODODENDRON:
                reds.append(extra)
            elif extra.species == Species.GERANIUM:
                greens.append(extra)
            else:
                blues.append(extra)

        # merge selected set
        self.varieties = reds + greens + blues
        # --- end selection change ---  # <<< CHANGED >>>

        cx = self.garden.width / 2.0
        cy = self.garden.height / 2.0

        # If any species missing, just do balanced adaptive packing on everything.
        if not reds or not greens or not blues:
            queue = sorted(self.varieties, key=self._cooperation_score, reverse=True)
            failed = self._pack_adaptive(queue, cx, cy)
            print('[Placement] Missing a species → no core triangle.')
            self._print_graph_stats('After placement (no-core)')
            self._refine_with_failed_pool(failed)
            self._print_graph_stats('After refinement (no-core)')
            return

        # Sort again for main process
        reds.sort(key=self._cooperation_score, reverse=True)
        greens.sort(key=self._cooperation_score, reverse=True)
        blues.sort(key=self._cooperation_score, reverse=True)

        # 1) Core triangle
        r, g, b = reds.pop(0), greens.pop(0), blues.pop(0)
        self._place_core_triangle(r, g, b, cx, cy)

        # 2) Balanced queue for remaining plants, largest first inside each species
        for group in (reds, greens, blues):
            group.sort(key=lambda v: (v.radius, self._cooperation_score(v)), reverse=True)
        queue = self._balanced_queue(reds, greens, blues)

        # 3) Adaptive packing
        failed = self._pack_adaptive(queue, cx, cy)

        # 4) Print stats after placement
        print('[Placement] Finished initial placement.')
        self._print_graph_stats('After placement')

        if failed:
            print(f'[Placement] Unplaced plants remaining: {len(failed)}')

        # 5) Refinement: try to bridge isolated/low-degree nodes with failed pool
        self._refine_with_failed_pool(failed)

        # 6) Final stats
        self._print_graph_stats('After refinement')
