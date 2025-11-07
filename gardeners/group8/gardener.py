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
        self.recent_anchors = deque(maxlen=75)

    def cultivate_garden(self) -> None:
        """Separate varieties by species, sort by quality, and place them in the garden."""
        rhodos = [v for v in self.varieties if v.species == Species.RHODODENDRON]
        geraniums = [v for v in self.varieties if v.species == Species.GERANIUM]
        begonias = [v for v in self.varieties if v.species == Species.BEGONIA]

        for species_list in [rhodos, geraniums, begonias]:
            species_list.sort(key=lambda v: (v.radius, -self.score_variety(v)))

        self.variety_scores = {id(v): self.score_variety(v) for v in self.varieties}

        self.place_plants(rhodos, geraniums, begonias)

    def score_variety(self, variety: PlantVariety) -> float:
        """Score variety by nutrient efficiency: (own_production - other_consumption) / radius²"""
        coeffs = variety.nutrient_coefficients

        if variety.species == Species.RHODODENDRON:
            own_production = coeffs.get(Micronutrient.R, 0)
            other_consumption = abs(coeffs.get(Micronutrient.G, 0) + coeffs.get(Micronutrient.B, 0))
        elif variety.species == Species.GERANIUM:
            own_production = coeffs.get(Micronutrient.G, 0)
            other_consumption = abs(coeffs.get(Micronutrient.R, 0) + coeffs.get(Micronutrient.B, 0))
        else:
            own_production = coeffs.get(Micronutrient.B, 0)
            other_consumption = abs(coeffs.get(Micronutrient.R, 0) + coeffs.get(Micronutrient.G, 0))

        return (own_production - other_consumption) / (variety.radius**2)

    def local_exchange_score(self, variety: PlantVariety, pos: Position) -> float:
        """Compute an approximate nutrient exchange score with neighbors at a given position."""

        score = 0
        var_r = variety.radius

        for plant in self.garden.plants:
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
        """Place plants starting from an initial triad, then iteratively add remaining plants."""
        initial_plants = [rhodos[0], geraniums[0], begonias[0]]
        initial_plants.sort(key=lambda x: x.radius, reverse=True)
        plant1, plant2, plant3 = initial_plants

        side = max(plant1.radius, plant2.radius, plant3.radius)
        height = side * math.sqrt(3) / 2

        self.garden.add_plant(plant1, Position(0, 0))
        self.recent_anchors.append(self.garden.plants[-1])
        self.garden.add_plant(plant2, Position(side, 0))
        self.recent_anchors.append(self.garden.plants[-1])
        self.garden.add_plant(plant3, Position(side / 2, height))
        self.recent_anchors.append(self.garden.plants[-1])

        species_data = {
            'R': rhodos,
            'G': geraniums,
            'B': begonias,
        }

        while any(len(species_data[s]) > 1 for s in species_data):
            best_placement = None
            best_score = -1

            for species_type, varieties in species_data.items():
                for i in range(1, len(varieties)):
                    variety = varieties[i]
                    pos = self.find_position_with_diverse_neighbors(variety)

                    if pos and self.garden.can_place_plant(variety, pos):
                        placement_score = self.variety_scores[id(variety)] + self.local_exchange_score(variety, pos)

                        if placement_score > best_score:
                            best_score = placement_score
                            best_placement = (species_type, variety, pos, i)

            if best_placement:
                species_type, variety, pos, variety_idx = best_placement
                self.garden.add_plant(variety, pos)
                self.recent_anchors.append(self.garden.plants[-1])
                species_data[species_type].pop(variety_idx)
            else:
                break

    def find_position_with_diverse_neighbors(self, variety):
        """Find position that ensures 2+ different-species neighbors."""
        if not self.garden.plants:
            return None

        best_pos = None
        best_score = -1
        var_r = variety.radius

        anchors = self.recent_anchors or self.garden.plants
        for anchor in anchors:
            if anchor.variety.species == variety.species:
                continue

            dist = max(variety.radius, anchor.variety.radius)
            for angle in range(0, 360, 15):
                x = anchor.position.x + dist * math.cos(math.radians(angle))
                y = anchor.position.y + dist * math.sin(math.radians(angle))

                if not (0 <= x <= self.garden.width and 0 <= y <= self.garden.height):
                    continue

                neighbor_species = set()
                valid = True

                for plant in self.garden.plants:
                    dx = x - plant.position.x
                    dy = y - plant.position.y
                    dist_sq = dx * dx + dy * dy

                    r_limit = max(var_r, plant.variety.radius)
                    if dist_sq < r_limit * r_limit:
                        valid = False
                        break

                if not valid:
                    continue

                for plant in self.garden.plants:
                    dx = x - plant.position.x
                    dy = y - plant.position.y
                    dist_sq = dx * dx + dy * dy
                    r_sum = var_r + plant.variety.radius

                    if dist_sq < r_sum * r_sum:
                        if plant.variety.species == variety.species:
                            valid = False
                            break
                        neighbor_species.add(plant.variety.species)
                        if len(neighbor_species) >= 2:
                            break

                if valid and len(neighbor_species) >= 2:
                    score = self.local_exchange_score(variety, Position(x, y))

                    if score > best_score:
                        best_score = score
                        best_pos = Position(x, y)

        return best_pos
