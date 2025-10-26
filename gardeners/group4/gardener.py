from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
import math
import random
from dataclasses import dataclass
from core.point import Position

class Gardener4(Gardener): 
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        # ---- Config (can be tweaked) ----
        TARGET_DEG = 3               # ideal number of interaction partners per plant
        W_INTER   = 10.0             # reward weight for cross-species interaction
        W_SAME    = 6.0              # penalty weight for same-species interaction
        W_DEG     = 2.0              # degree regularizer strength
        CAND_MULT = 2.0              # density multiplier for candidate lattice
        RAND_JIG  = 0.35             # random jitter fraction of local step (to break ties)
        MAX_TRIES_PER_PLANT = 200    # candidate attempts per plant

        # ---- Garden extents (robust fallbacks) ----
        W = getattr(self.garden, "width",  None) or getattr(self.garden, "W", None) or 100
        H = getattr(self.garden, "height", None) or getattr(self.garden, "H", None) or 100

        # ---- Utilities ----
        @dataclass
        class Placed:
            x: int
            y: int
            r: int
            species: object

        def spacing_ok(x:int, y:int, r:int, placed:list[Placed]) -> bool:
            """Centers must be >= max(r_i, r_j) apart."""
            for p in placed:
                dx = x - p.x
                dy = y - p.y
                d = math.hypot(dx, dy)
                if d < max(r, p.r) - 1e-9:
                    return False
            return True

        def interaction_window(d:float, ri:int, rj:int) -> float:
            """
            Returns a 'bump' reward on [max(ri,rj), ri+rj):
            0 outside; rises toward the middle; drops near boundaries.
            """
            lo = max(ri, rj)
            hi = ri + rj
            if d <= lo or d >= hi:
                return 0.0
            # Smooth bump: product of distances to each boundary
            return (hi - d) * (d - lo)

        def score_position(x:int, y:int, r:int, species, placed:list[Placed]) -> float:
            """Higher is better; includes degree regularization toward TARGET_DEG."""
            deg = 0
            s = 0.0
            for p in placed:
                dx = x - p.x
                dy = y - p.y
                d = math.hypot(dx, dy)
                if species != p.species:
                    bump = interaction_window(d, r, p.r)
                    if bump > 0:
                        s += W_INTER * bump
                        deg += 1
                else:
                    # Prefer same-species distances outside interaction range
                    bump = interaction_window(d, r, p.r)
                    if bump > 0:
                        s -= W_SAME * bump
            # Degree regularizer (soft cap around TARGET_DEG)
            s -= W_DEG * max(0, deg - TARGET_DEG) ** 2
            return s

        # Triangular lattice candidates (denser than strict spacing to give options)
        radii = [v.radius for v in self.varieties]
        if not radii:
            return
        r_min = max(1, min(radii))
        # Base lattice step aims to put many pairs inside interaction while respecting spacing
        base_step = max(1.0, 1.6 * r_min)
        step = max(1.0, base_step / CAND_MULT)

        def candidate_positions():
            """Generate a triangular lattice of integer positions, shuffled."""
            pts = []
            y = 0.0
            row = 0
            while y <= H:
                x_offset = (0.5 * step) if (row % 2 == 1) else 0.0
                x = x_offset
                while x <= W:
                    xi = int(round(x))
                    yi = int(round(y))
                    # clamp inside garden bounds
                    xi = max(0, min(int(W), xi))
                    yi = max(0, min(int(H), yi))
                    pts.append((xi, yi))
                    x += step
                y += step * math.sin(math.radians(60))  # vertical spacing for triangular grid
                row += 1
            random.shuffle(pts)
            return pts

        lattice = candidate_positions()

        # Sorted placement: largest radii first (clear big constraints early)
        random.shuffle(self.varieties)

        placed: list[Placed] = []
        used_cells: set[tuple[int,int]] = set()

        # Species ID helper (stable equality even if enum/class differs)
        def sp_key(s): 
            return getattr(s, "name", None) or getattr(s, "value", None) or str(s)

        for var in self.varieties:
            r = int(var.radius)
            sk = sp_key(var.species)

            best = None  # (score, x, y)
            tries = 0

            # Iterate through lattice with small random jitter to avoid perfect symmetry
            for (cx, cy) in lattice:
                if tries >= MAX_TRIES_PER_PLANT and best is not None:
                    break
                tries += 1

                # jitter around the lattice point (fraction of step), keep inside
                jx = int(round(cx + (RAND_JIG * step) * (random.random() * 2 - 1)))
                jy = int(round(cy + (RAND_JIG * step) * (random.random() * 2 - 1)))
                x = max(0, min(int(W), jx))
                y = max(0, min(int(H), jy))

                if (x, y) in used_cells:
                    continue
                if not spacing_ok(x, y, r, placed):
                    continue

                sc = score_position(x, y, r, sk, placed)
                if (best is None) or (sc > best[0]):
                    best = (sc, x, y)

            # If lattice search fails to find anything (very dense), fall back to random
            if best is None:
                for _ in range(MAX_TRIES_PER_PLANT):
                    x = random.randint(0, int(W))
                    y = random.randint(0, int(H))
                    if not spacing_ok(x, y, r, placed):
                        continue
                    sc = score_position(x, y, r, sk, placed)
                    if (best is None) or (sc > best[0]):
                        best = (sc, x, y)

            # Final placement attempt(s)
            if best is not None:
                _, bx, by = best
                pos = Position(bx, by)
                planted = self.garden.add_plant(var, pos)
                if planted is not None:
                    placed.append(Placed(pos.x, pos.y, r, sk))
                    used_cells.add((pos.x, pos.y))
                    continue  # next variety

            # If everything failed (extremely crowded), place greedily anywhere legal
            fallback_done = False
            for _ in range(10 * MAX_TRIES_PER_PLANT):
                x = random.randint(0, int(W))
                y = random.randint(0, int(H))
                if spacing_ok(x, y, r, placed):
                    pos = Position(x, y)
                    planted = self.garden.add_plant(var, pos)
                    if planted is not None:
                        placed.append(Placed(pos.x, pos.y, r, sk))
                        used_cells.add((pos.x, pos.y))
                        fallback_done = True
                        break
            if not fallback_done:
                # Give up on this variety if garden refuses (e.g., capacity rules)
                # Silently skip; simulation will proceed with existing plants.
                pass
