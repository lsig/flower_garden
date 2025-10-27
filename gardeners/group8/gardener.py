from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position
from core.micronutrients import Micronutrient
import math


class Gardener8(Gardener):
    """Repeats best scoring RGB triad, places leftovers if species counts are imbalanced."""

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        # divide varieties by species
        rhods = [v for v in self.varieties if v.species == Species.RHODODENDRON]
        gers = [v for v in self.varieties if v.species == Species.GERANIUM]
        begs = [v for v in self.varieties if v.species == Species.BEGONIA]

        if not (rhods and gers and begs):
            # if no full triads possible, just place everything in a grid
            self.place_leftovers(self.varieties)
            return

        # generate all triads and sort by score
        triage = self.generate_triage()
        print('Top 5 triage scores and combinations:')
        for score, r, g, b in triage[:5]:
            print(f'Score: {score:.2f}, R: {r.name}, G: {g.name}, B: {b.name}')

        # select the best triad
        _, R, G, B = triage[0]

        # set up spacing for triangular placement
        garden_w, garden_h = self.garden.width, self.garden.height

        # making equilateral triangles, in a lattice of sorts
        spacing = 2 * max(
            R.radius, G.radius, B.radius
        )  # horizontal space btwn plants along base of triangle
        # def overly conservative, tweak later. but no risk of root overlap btwn nearby same-species plants

        dx = spacing / 2  # horizontal offset for plants in next row
        dy = spacing * math.sin(
            math.pi / 3
        )  # height of the triangle - this becomes vertical offset to next row

        # just starting coords for placement
        x = 0.0
        y = 0.0
        row_shift = False  # tells whether this row should have the horizontal offset or not
        # (since we're doing a lattice)

        # track remaining plants of each species
        remaining = {
            Species.RHODODENDRON: rhods[:],
            Species.GERANIUM: gers[:],
            Species.BEGONIA: begs[:],
        }

        # Place triads across the garden
        while y < garden_h:  # loop vertically through rows
            x = (
                0.0 if not row_shift else dx
            )  # does the horizontal shift for the row depending on the flag
            while x < garden_w:  # loop horizontally through the row
                triad_plants = []
                for sp in [
                    Species.RHODODENDRON,
                    Species.GERANIUM,
                    Species.BEGONIA,
                ]:  # form the triad!
                    if remaining[sp]:
                        triad_plants.append(remaining[sp].pop(0))
                    else:
                        triad_plants.append(
                            None
                        )  # but if a species is missing, just add None to the triad

                if any(triad_plants):  # if the triad has a plant, place it
                    self.place_triad(
                        *triad_plants, x, y
                    )  # at the right horizontal / vertical offset

                x += spacing * 1.5  # to make sure triangles don't overlap
            y += dy  # increment by the vertical offset we calculated
            row_shift = not row_shift  # toggle whether to shift the next row or not

    def generate_triage(self):
        """Generate all possible RGB triage and score them."""
        species_map = {Species.RHODODENDRON: [], Species.GERANIUM: [], Species.BEGONIA: []}

        for variety in self.varieties:
            if variety.species in species_map:
                species_map[variety.species].append(variety)

        triage = [
            (self.score_triage(r, g, b), r, g, b)
            for r in species_map[Species.RHODODENDRON]
            for g in species_map[Species.GERANIUM]
            for b in species_map[Species.BEGONIA]
        ]

        return sorted(triage, key=lambda x: x[0], reverse=True)

    def place_triad(self, r, g, b, x, y):
        """Place triad as an equilateral triangle, skipping any None plants."""
        # makes sure plants aren't closer than their neighbors than their radius
        # default tho just in case all the plants are none
        spacing = 2 * max((p.radius for p in [r, g, b] if p), default=1)

        dx = spacing / 2  # horizontal offset for plants in next row
        dy = spacing * math.sin(
            math.pi / 3
        )  # height of the triangle - this becomes vertical offset to next row

        # plant r goes at 0,0, g is above, and b is horizontally aligned with r. equilateral triangle
        offsets = [(0, 0), (dx, dy / 2), (2 * dx, 0)]
        plants = [r, g, b]

        for plant, (ox, oy) in zip(plants, offsets):  # loop over plants and their offsets
            if plant is None:  # in case triad has missing species
                continue
            pos = Position(x + ox, y + oy)  # calculate position using offets
            if self.garden.can_place_plant(plant, pos):  # validate placement
                self.garden.add_plant(plant, pos)  # add plant

    def place_leftovers(self, plants):
        """Place leftover plants in a simple grid."""
        if not plants:
            return

        # starting position
        x = 0.0
        y = 0.0
        row_shift = False
        garden_w, garden_h = self.garden.width, self.garden.height

        for plant in plants:
            spacing = 2 * plant.radius
            pos = Position(x, y)
            if self.garden.can_place_plant(plant, pos):
                self.garden.add_plant(plant, pos)

            # same spacing logic, just one by one (no triad)
            x += spacing * 1.5
            if x + spacing > garden_w:
                x = 0.0 if not row_shift else spacing / 2
                y += spacing * math.sin(math.pi / 3)
                row_shift = not row_shift

    def score_triage(self, r, g, b):
        """Score a cluster by growth rate x nutrient sustainability."""
        # production of nutrients
        prod = {
            Micronutrient.R: r.nutrient_coefficients[Micronutrient.R],
            Micronutrient.G: g.nutrient_coefficients[Micronutrient.G],
            Micronutrient.B: b.nutrient_coefficients[Micronutrient.B],
        }
        cons = {
            Micronutrient.R: abs(g.nutrient_coefficients[Micronutrient.R])
            + abs(b.nutrient_coefficients[Micronutrient.R]),
            Micronutrient.G: abs(r.nutrient_coefficients[Micronutrient.G])
            + abs(b.nutrient_coefficients[Micronutrient.G]),
            Micronutrient.B: abs(r.nutrient_coefficients[Micronutrient.B])
            + abs(g.nutrient_coefficients[Micronutrient.B]),
        }

        # nutrient score is the minimum surplus across all nutrients
        nutrient_score = min(prod[n] - cons[n] for n in prod)

        # growth rate is the sum of the radii
        growth_rate = r.radius + g.radius + b.radius

        return nutrient_score * 0.8 + growth_rate * 0.2
