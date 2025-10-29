import math
from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener8(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def cultivate_garden(self) -> None:
        """Separate varieties by species, sort by quality, and place them in the garden."""
        #separate varieties by species
        rhodos = [v for v in self.varieties if v.species == Species.RHODODENDRON]
        geraniums = [v for v in self.varieties if v.species == Species.GERANIUM]
        begonias = [v for v in self.varieties if v.species == Species.BEGONIA]

        # sort each species by radius (smallest first), then by score (highest first)
        for species_list in [rhodos, geraniums, begonias]:
            species_list.sort(key=lambda v: (v.radius, -self.score_variety(v)))

        # place plants in interlocking triangular groups
        self.place_plants(rhodos, geraniums, begonias)

    def score_variety(self, variety: PlantVariety) -> float:
        """
        Score variety by nutrient efficiency and spatial efficiency.

        Formula: (own_production - other_consumption) / radius²
        where own_production is the plant's production of its species' nutrient,
        and other_consumption is the absolute value of consumption of other nutrients.
        """
        coeffs = variety.nutrient_coefficients

        #get the production of the plant's own nutrient type and consumption of others
        if variety.species == Species.RHODODENDRON:
            own_production = coeffs.get(Micronutrient.R, 0)
            other_consumption = abs(coeffs.get(Micronutrient.G, 0) + coeffs.get(Micronutrient.B, 0))
        elif variety.species == Species.GERANIUM:
            own_production = coeffs.get(Micronutrient.G, 0)
            other_consumption = abs(coeffs.get(Micronutrient.R, 0) + coeffs.get(Micronutrient.B, 0))
        else:  #BEGONIA
            own_production = coeffs.get(Micronutrient.B, 0)
            other_consumption = abs(coeffs.get(Micronutrient.R, 0) + coeffs.get(Micronutrient.G, 0))

        #score balances own production vs other consumption, penalized by radius
        return (own_production - other_consumption) / (variety.radius ** 2)

    def place_plants(self, rhodos, geraniums, begonias):
        """
        Place all plants starting from an initial triad.

        First places one rhododendron, geranium, and begonia in a triangular formation.
        Then iteratively places remaining plants by finding the best variety-position
        combination that maximizes score while maintaining 2+ different-species neighbors.
        """
        # this initial placement can be played around with
        # place initial triad in bottom-left quadrant
        start_x = self.garden.width / 4
        start_y = self.garden.height / 4

        r1, g1, b1 = rhodos[0], geraniums[0], begonias[0]

        # Pairwise plant combinations
        pairs = [(r1, g1), (r1, b1), (g1, b1)]

        # Compute min/max distances for each pair
        # min_distance = largest radius (avoid one inside another)
        # max_distance = sum of radii (ensures interaction)
        min_dists = [max(p[0].radius, p[1].radius) for p in pairs]
        max_dists = [p[0].radius + p[1].radius for p in pairs]

        # Determine spacing for the triad
        min_required = max(min_dists)  # safe minimum to prevent overlap
        max_allowed = min(max_dists)   # max distance that still allows interaction

        if min_required <= max_allowed:
            # feasible: all pairs can interact, pick 50% toward max for extra space (can be tweaked)
            side = min_required + 0.5 * (max_allowed - min_required)
        else:
            # no single distance fits all, stick to min_required to avoid overlap
            side = min_required

        # Compute height for equilateral layout
        height = side * math.sqrt(3) / 2

        p_r = Position(start_x, start_y - height / 3)
        p_g = Position(start_x - side / 2, start_y + 2 * height / 3)
        p_b = Position(start_x + side / 2, start_y + 2 * height / 3)

        #place the initial triad
        self.garden.add_plant(r1, p_r)
        self.garden.add_plant(g1, p_g)
        self.garden.add_plant(b1, p_b)

        indices = {'R': 1, 'G': 1, 'B': 1}
        species_data = {
            'R': (rhodos, [Species.GERANIUM, Species.BEGONIA]),
            'G': (geraniums, [Species.RHODODENDRON, Species.BEGONIA]),
            'B': (begonias, [Species.RHODODENDRON, Species.GERANIUM])
        }

        # iteratively place remaining plants until no more can be placed
        stuck_counter = 0
        while stuck_counter < 50:
            #check if all species exhausted
            if all(indices[s] >= len(species_data[s][0]) for s in indices):
                break

            best_placement = None
            best_score = -1

            # Evaluate ALL remaining varieties from all species
            for species_type, (varieties, required_species) in species_data.items():
                # Get the current variety index for this species type
                idx = indices[species_type]

                # Check all remaining varieties for this species
                for i in range(idx, len(varieties)):
                    variety = varieties[i]

                    # Find a position that maximizes neighbor diversity
                    pos = self.find_position_with_diverse_neighbors(variety, required_species)

                    # Verify the position is valid and the plant can be placed there
                    if pos and self.garden.can_place_plant(variety, pos):
                        # Calculate how valuable this placement would be
                        placement_score = self.score_variety(variety)

                        # Keep track of the best placement found so far
                        if placement_score > best_score:
                            best_score = placement_score
                            best_placement = (species_type, variety, pos, i)

            #place the best variety-position combination
            if best_placement:
                species_type, variety, pos, variety_idx = best_placement
                self.garden.add_plant(variety, pos)
                # Remove the placed variety from the list to avoid re-evaluating it
                species_data[species_type][0].pop(variety_idx)
                stuck_counter = 0
            else:
                stuck_counter += 1

#this can def be imporved no need for fix distance probably and angles
    def find_position_with_diverse_neighbors(self, variety, required_species):
        """
        Find a valid position for a variety that ensures 2+ different-species neighbors.

        Searches around existing plants at different distances (75%, 85% of combined radii)
        and angles (every 30 degrees). Scores positions by diversity and tightness.
        Returns the best position found, or None if no valid position exists.
        """
        if not self.garden.plants:
            return None

        best_pos = None
        best_score = -1

        #try positions around each existing plant
        for anchor in self.garden.plants:
            if anchor.variety.species == variety.species:
                continue

            # test positions at different distances and angles
            for distance_mult in [0.75, 0.85]:
                dist = (variety.radius + anchor.variety.radius) * distance_mult

                for angle in range(0, 360, 30):
                    x = anchor.position.x + dist * math.cos(math.radians(angle))
                    y = anchor.position.y + dist * math.sin(math.radians(angle))

                    if not (0 <= x <= self.garden.width and 0 <= y <= self.garden.height):
                        continue

                    # check validity and count diverse neighbors
                    neighbor_species = set()
                    valid = True

                    for plant in self.garden.plants:
                        d = math.sqrt((x - plant.position.x)**2 + (y - plant.position.y)**2)

                        if d < max(variety.radius, plant.variety.radius):
                            valid = False
                            break

                        if d < variety.radius + plant.variety.radius:
                            if plant.variety.species == variety.species:
                                valid = False
                                break
                            neighbor_species.add(plant.variety.species)

                    #require 2+ different species neighbors
                    if valid and len(neighbor_species) >= 2:
                        score = len(neighbor_species) * 10 + (1.0 - distance_mult) * 5
                        if score > best_score:
                            best_score = score
                            best_pos = Position(x, y)

        return best_pos



