import math
from collections import deque

from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener8(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        # sliding window of recently added plants instead of scanning every plant in the garden
        self.recent_anchors = deque(maxlen=25)

    def cultivate_garden(self) -> None:
        """Separate varieties by species, sort by quality, and place them in the garden."""
        # separate varieties by species
        rhodos = [v for v in self.varieties if v.species == Species.RHODODENDRON]
        geraniums = [v for v in self.varieties if v.species == Species.GERANIUM]
        begonias = [v for v in self.varieties if v.species == Species.BEGONIA]

        # sort each species by radius (smallest first), then by score (highest first)
        for species_list in [rhodos, geraniums, begonias]:
            species_list.sort(key=lambda v: (v.radius, -self.score_variety(v)))

        # cache the variety scores
        # base score is computed once and stored
        self.variety_scores = {id(v): self.score_variety(v) for v in self.varieties}

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

        # get the production of the plant's own nutrient type and consumption of others
        if variety.species == Species.RHODODENDRON:
            own_production = coeffs.get(Micronutrient.R, 0)
            other_consumption = abs(coeffs.get(Micronutrient.G, 0) + coeffs.get(Micronutrient.B, 0))
        elif variety.species == Species.GERANIUM:
            own_production = coeffs.get(Micronutrient.G, 0)
            other_consumption = abs(coeffs.get(Micronutrient.R, 0) + coeffs.get(Micronutrient.B, 0))
        else:  # BEGONIA
            own_production = coeffs.get(Micronutrient.B, 0)
            other_consumption = abs(coeffs.get(Micronutrient.R, 0) + coeffs.get(Micronutrient.G, 0))

        # score balances own production vs other consumption, penalized by radius
        return (own_production - other_consumption) / (variety.radius**2)

    def local_exchange_score(self, variety: PlantVariety, pos: Position) -> float:
        """Compute an approximate nutrient exchange score with neighbors at a given position."""

        score = 0
        var_r = variety.radius

        for plant in self.garden.plants:
            # check distance for interaction
            dx = pos.x - plant.position.x
            dy = pos.y - plant.position.y
            dist_sq = dx * dx + dy * dy
            r_sum = var_r + plant.variety.radius
            if dist_sq >= r_sum * r_sum:
                continue  # too far to interact

            for nut in [Micronutrient.R, Micronutrient.G, Micronutrient.B]:
                # inventory caps
                our_capacity = 10 * var_r
                neighbor_capacity = 10 * plant.variety.radius

                # rough current inventory estimate (use 50% full as proxy, since not currently tracking)
                our_inv = 0.5 * our_capacity
                neighbor_inv = 0.5 * neighbor_capacity

                # how much each produces (per tick) - could be nutrient_coefficients * rv
                our_prod = max(0, variety.nutrient_coefficients.get(nut, 0))
                neighbor_prod = max(0, plant.variety.nutrient_coefficients.get(nut, 0))

                # how much they can offer (1/4 of current inventory)
                our_offer = min(our_prod, 0.25 * our_inv)
                neighbor_offer = min(neighbor_prod, 0.25 * neighbor_inv)

                # actual exchange = min(what we offer, what neighbor offers)
                exchange_amount = min(our_offer, neighbor_offer)

                # compute a scarcity rating
                # prefer adding plants that produce what is currently missing
                total_abs = sum(
                    abs(v.variety.nutrient_coefficients[nut]) for v in self.garden.plants
                )
                deficit_weight = 1 / max(1e-6, total_abs)

                # only count if giving > receiving
                if our_offer > neighbor_offer:
                    score += exchange_amount * deficit_weight  # benefit to neighbor
                if neighbor_offer > our_offer:
                    score += exchange_amount * deficit_weight  # benefit to us
        # normalizing the score
        return score / max(1, len(self.garden.plants))

    def place_plants(self, rhodos, geraniums, begonias):
        """
        Place all plants starting from an initial triad.

        First places one rhododendron, geranium, and begonia in a triangular formation.
        Then iteratively places remaining plants by finding the best variety-position
        combination that maximizes score while maintaining 2+ different-species neighbors.
        """
        r1, g1, b1 = rhodos[0], geraniums[0], begonias[0]

        # Sort the initial triad by radius to find the largest
        initial_plants = [r1, g1, b1]
        initial_plants.sort(key=lambda x: x.radius, reverse=True)

        plant1, plant2, plant3 = initial_plants

        # Pairwise plant combinations
        pairs = [(plant1, plant2), (plant1, plant3), (plant2, plant3)]

        # Compute min/max distances for each pair
        # min_distance = largest radius (avoid one inside another)
        # max_distance = sum of radii (ensures interaction)
        min_dists = [max(p[0].radius, p[1].radius) for p in pairs]
        max_dists = [p[0].radius + p[1].radius for p in pairs]

        # Determine spacing for the triad
        min_required = max(min_dists)  # safe minimum to prevent overlap
        max_allowed = min(max_dists)  # max distance that still allows interaction

        if min_required <= max_allowed:
            # feasible: all pairs can interact, pick 50% toward max for extra space (can be tweaked)
            side = min_required + 0.5 * (max_allowed - min_required)
        else:
            # no single distance fits all, stick to min_required to avoid overlap
            side = min_required

        # Compute height for equilateral layout
        height = side * math.sqrt(3) / 2

        # Place largest plant's center at (0, 0) - roots can extend outside garden
        p1 = Position(0, 0)
        # Place second plant to the right
        p2 = Position(side, 0)
        # Place third plant above to form equilateral triangle
        p3 = Position(side / 2, height)

        # place the initial triad
        self.garden.add_plant(plant1, p1)
        self.recent_anchors.append(self.garden.plants[-1])
        self.garden.add_plant(plant2, p2)
        self.recent_anchors.append(self.garden.plants[-1])
        self.garden.add_plant(plant3, p3)
        self.recent_anchors.append(self.garden.plants[-1])

        indices = {'R': 1, 'G': 1, 'B': 1}
        species_data = {
            'R': (rhodos, [Species.GERANIUM, Species.BEGONIA]),
            'G': (geraniums, [Species.RHODODENDRON, Species.BEGONIA]),
            'B': (begonias, [Species.RHODODENDRON, Species.GERANIUM]),
        }

        # iteratively place remaining plants until no more can be placed
        stuck_counter = 0
        while stuck_counter < 10:
            # check if all species exhausted
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
                        local_weight = 0.05 + 0.05 * min(1, len(self.garden.plants) / 100)
                        placement_score = self.variety_scores[
                            id(variety)
                        ] + local_weight * self.local_exchange_score(variety, pos)

                        # Keep track of the best placement found so far
                        if placement_score > best_score:
                            best_score = placement_score
                            best_placement = (species_type, variety, pos, i)

            # place the best variety-position combination
            if best_placement:
                species_type, variety, pos, variety_idx = best_placement
                self.garden.add_plant(variety, pos)
                self.recent_anchors.append(self.garden.plants[-1])
                # Remove the placed variety from the list to avoid re-evaluating it
                species_data[species_type][0].pop(variety_idx)
                stuck_counter = 0
            else:
                stuck_counter += 1

    # this can def be imporved no need for fix distance probably and angles
    def find_position_with_diverse_neighbors(self, variety, required_species):
        """
        Optimized placement search that tries to ensure 2+ different-species neighbors.

        Early rejection:
            - Out of bounds check (cheap)
            - Same-species overlap check using squared distance
            - Full neighbor scan only if above checks pass
        """
        if not self.garden.plants:
            return None

        best_pos = None
        best_score = -1
        var_r = variety.radius

        # loop through anchors
        anchors = self.recent_anchors or self.garden.plants
        for anchor in anchors:
            if anchor.variety.species == variety.species:
                continue

            anchor_x = anchor.position.x
            anchor_y = anchor.position.y

            # Always place as compactly as possible
            dist = max(variety.radius, anchor.variety.radius)
            # experiment with the last parameter for the angle here
            for angle in range(0, 360, 15):
                x = anchor_x + dist * math.cos(math.radians(angle))
                y = anchor_y + dist * math.sin(math.radians(angle))

                # quick bounds check
                if not (0 <= x <= self.garden.width and 0 <= y <= self.garden.height):
                    continue

                # pre-calc avoid sqrt
                neighbor_species = set()
                valid = True

                # cheap screening first: same-species spacing
                for plant in self.garden.plants:
                    dx = x - plant.position.x
                    dy = y - plant.position.y
                    dist_sq = dx * dx + dy * dy

                    # squared overlap check (cheap)
                    r_limit = max(var_r, plant.variety.radius)
                    if dist_sq < r_limit * r_limit:  # too close → invalid
                        valid = False
                        break

                if not valid:
                    continue  # skip further checks

                # now check interaction neighbors only if still valid
                for plant in self.garden.plants:
                    dx = x - plant.position.x
                    dy = y - plant.position.y
                    dist_sq = dx * dx + dy * dy
                    r_sum = var_r + plant.variety.radius

                    if dist_sq < r_sum * r_sum:
                        # interacting neighbor
                        if plant.variety.species == variety.species:
                            valid = False
                            break
                        neighbor_species.add(plant.variety.species)
                        if len(neighbor_species) >= 2:
                            break

                # need 2+ other species neighbors for exchange
                if valid and len(neighbor_species) >= 2:
                    score = len(neighbor_species) + 0.1 * self.local_exchange_score(
                        variety, Position(x, y)
                    )
                    if score > best_score:
                        best_score = score
                        best_pos = Position(x, y)

        return best_pos
