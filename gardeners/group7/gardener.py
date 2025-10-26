import math
from collections import defaultdict

from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener7(Gardener):
    def __init__(self, garden, varieties):
        # Expand varieties if they include a "count" attribute so each plant is its own instance
        expanded = []
        for v in varieties:
            count = getattr(v, 'count', 1)
            for _ in range(count):
                expanded.append(
                    PlantVariety(
                        name=v.name,
                        radius=v.radius,
                        species=v.species,
                        nutrient_coefficients=dict(v.nutrient_coefficients),
                    )
                )
        # Initialize base class with actual list of plant items
        super().__init__(garden, expanded)

    def _cooperation_score(self, v):
        # Retrieve R,G,B production/consumption values
        R = v.nutrient_coefficients.get('R', 0)
        G = v.nutrient_coefficients.get('G', 0)
        B = v.nutrient_coefficients.get('B', 0)

        # Surplus is anything positive, deficit is negative turned positive for comparison
        surpluses = [max(R, 0), max(G, 0), max(B, 0)]
        deficits = [abs(min(R, 0)), abs(min(G, 0)), abs(min(B, 0))]

        # The most valuable characteristics are strong production and strong need
        best_surplus = max(surpluses)
        best_deficit = max(deficits)

        # Plants with both a strong production and a strong need contribute most to exchange
        return best_surplus * best_deficit

    def cultivate_garden(self) -> None:
        # Split plants by species to later build an RGB interaction network
        reds = [v for v in self.varieties if v.species == Species.RHODODENDRON]
        greens = [v for v in self.varieties if v.species == Species.GERANIUM]
        blues = [v for v in self.varieties if v.species == Species.BEGONIA]

        # Sort each group by compatibility score and then size
        def sort_key(v):
            return (self._cooperation_score(v), v.radius)

        reds.sort(key=sort_key, reverse=True)
        greens.sort(key=sort_key, reverse=True)
        blues.sort(key=sort_key, reverse=True)

        # Calculate center of garden for initial placements
        cx = self.garden.width / 2.0
        cy = self.garden.height / 2.0

        # Build a strong central triangle using highest-value plant of each species
        r = reds.pop(0)
        g = greens.pop(0)
        b = blues.pop(0)

        # Order those three by radius so largest is fully centered
        core = sorted([r, g, b], key=lambda v: v.radius, reverse=True)
        p0, p1, p2 = core[0], core[1], core[2]

        # Place largest at exact center
        self.garden.add_plant(p0, Position(cx, cy))

        # Compute ideal distances to create strong but non-violating overlap
        eps = 0.2
        a = p0.radius + p1.radius - eps
        bdist = p0.radius + p2.radius - eps
        c = p1.radius + p2.radius - eps

        # Ensure triangle inequality remains valid
        tiny = 1e-3
        for _ in range(3):
            if a >= bdist + c:
                a = bdist + c - tiny
            if bdist >= a + c:
                bdist = a + c - tiny
            if c >= a + bdist:
                c = a + bdist - tiny
            if a <= abs(bdist - c):
                a = abs(bdist - c) + tiny
            if bdist <= abs(a - c):
                bdist = abs(a - c) + tiny
            if c <= abs(a - bdist):
                c = abs(a - bdist) + tiny

        # Place second plant along x-axis at correct overlap distance
        x1 = cx + a
        y1 = cy
        self.garden.add_plant(p1, Position(x1, y1))

        # Compute the intersection point for the third plant
        x2, y2 = self._circle_intersection(cx, cy, bdist, x1, y1, c, choose_upper=True)

        # Slightly pull the point inward to improve overlap strength
        def pull_toward(xa, ya, xb, yb, factor):
            return xa + (xb - xa) * factor, ya + (yb - ya) * factor

        x2, y2 = pull_toward(x2, y2, cx, cy, 0.3)
        x2, y2 = pull_toward(x2, y2, x1, y1, 0.3)

        self.garden.add_plant(p2, Position(x2, y2))

        # Remaining plants sorted by cooperation priority
        leftovers = reds + greens + blues
        leftovers.sort(key=self._cooperation_score, reverse=True)

        # Group leftovers by species to possibly build another RGB triangle
        species_map = defaultdict(list)
        for v in leftovers:
            species_map[v.species].append(v)

        # Used as reference radius for secondary placement spacing
        core_dist = p0.radius + p1.radius + p2.radius

        # Build a second strong RGB triangle if one of each species is still available
        if all(species_map[sp] for sp in [Species.RHODODENDRON, Species.GERANIUM, Species.BEGONIA]):
            t0 = species_map[Species.RHODODENDRON].pop(0)
            t1 = species_map[Species.GERANIUM].pop(0)
            t2 = species_map[Species.BEGONIA].pop(0)

            triangle_dist = core_dist * 1.8
            angle_offset = math.pi / 6
            for i, v in enumerate([t0, t1, t2]):
                angle = angle_offset + i * (2 * math.pi / 3)
                px = cx + triangle_dist * math.cos(angle)
                py = cy + triangle_dist * math.sin(angle)
                self._safe_place(v, px, py)

            leftovers = (
                species_map[Species.RHODODENDRON]
                + species_map[Species.GERANIUM]
                + species_map[Species.BEGONIA]
            )

        # If less than three remain, spread them strategically opposite center
        elif len(leftovers) == 2:
            angles = [math.pi / 3, -math.pi / 3]
            for i, v in enumerate(leftovers):
                px = cx + core_dist * 2.0 * math.cos(angles[i])
                py = cy + core_dist * 2.0 * math.sin(angles[i])
                self._safe_place(v, px, py)
            leftovers = []

        elif len(leftovers) == 1:
            angle = math.pi
            px = cx + core_dist * 2.2 * math.cos(angle)
            py = cy + core_dist * 2.2 * math.sin(angle)
            self._safe_place(leftovers[0], px, py)
            leftovers = []

        # Place the remaining plants in a ring, highest cooperation first
        if leftovers:
            leftovers.sort(key=self._cooperation_score, reverse=True)

            # Determine how large the ring can be without leaving the garden
            usable_radius = min(cx, cy, self.garden.width - cx, self.garden.height - cy)
            margin = max(v.radius for v in leftovers) + 0.5
            max_ring = max(0.0, usable_radius - margin)

            ring_dist = min(core_dist * 2.2, max_ring)
            start_angle = math.pi / 6

            # Place them around the ring, trying small jitters to avoid overlap failures
            for i, v in enumerate(leftovers):
                placed = False
                for jitter in range(12):
                    angle = (
                        start_angle + i * (2 * math.pi / len(leftovers)) + jitter * (math.pi / 24)
                    )
                    px = cx + ring_dist * math.cos(angle)
                    py = cy + ring_dist * math.sin(angle)
                    if self._safe_place(v, px, py):
                        placed = True
                        break

                # If not placed yet, spiral inward slightly to find workable spot
                if not placed:
                    for step in range(1, 10):
                        r = ring_dist * (1 - 0.06 * step)
                        px = cx + r * math.cos(angle)
                        py = cy + r * math.sin(angle)
                        if self._safe_place(v, px, py):
                            break

    def _circle_intersection(self, x0, y0, r0, x1, y1, r1, choose_upper=True):
        # Computes intersection points of two circles centered at (x0,y0) and (x1,y1)
        dx = x1 - x0
        dy = y1 - y0
        d = math.hypot(dx, dy)

        # Solve the circle intersection geometry
        a = (r0**2 - r1**2 + d**2) / (2 * d)
        h_sq = max(0.0, r0**2 - a**2)
        h = math.sqrt(h_sq)

        xm = x0 + a * dx / d
        ym = y0 + a * dy / d

        rx = -dy * (h / d)
        ry = dx * (h / d)

        xi = xm + rx
        yi = ym + ry
        xi2 = xm - rx
        yi2 = ym - ry

        # Return the intersection based on orientation preference
        if choose_upper:
            return (xi, yi) if yi >= yi2 else (xi2, yi2)
        else:
            return (xi, yi) if yi < yi2 else (xi2, yi2)

    def _safe_place(self, variety, x, y):
        # Attempt slight jitters around the proposed location to avoid invalid placement
        for dx in [0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5]:
            for dy in [0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5]:
                px = x + dx
                py = y + dy
                # Only accept if inside boundaries and respecting root constraints
                if (
                    0.0 < px < self.garden.width
                    and 0.0 < py < self.garden.height
                    and self.garden.add_plant(variety, Position(px, py))
                ):
                    return True
        return False
