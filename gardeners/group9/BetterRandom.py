import copy
import random

from core.garden import Garden
from core.gardener import Gardener
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class BetterRandom(Gardener):
    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)

    def delete_plant(self, plant):
        if plant not in self.garden.plants:
            return False

        self.garden.plants.remove(plant)
        self.garden._used_varieties.discard(id(plant.variety))
        return True

    def plant_random_from_corner(self, VL):
        for variety in VL:
            # print(variety)
            Found = False
            starting_box = 0.1

            while not Found and starting_box < 1.2:
                for _ in range(100):
                    # print("here", Found, starting_box)
                    x = random.uniform(0, 100 * self.garden.width)
                    y = random.uniform(0, 100 * self.garden.height)
                    x *= starting_box / 100
                    y *= starting_box / 100

                    position = Position(x, y)

                    if self.garden.can_place_plant(variety, position):
                        self.garden.add_plant(variety, position)
                        Found = True
                        break
                if not Found:
                    starting_box += 0.1

    def has_RBG_neighbors(self, plant):
        red = False
        blue = False
        green = False

        # print(plant.variety.species)
        # input()

        if plant.variety.species == Species.RHODODENDRON:
            red = True
        elif plant.variety.species == Species.GERANIUM:
            green = True
        elif plant.variety.species == Species.BEGONIA:
            blue = True

        for neighbor in self.garden.get_interacting_plants(plant):
            if neighbor.variety.species == Species.RHODODENDRON:
                red = True
            elif neighbor.variety.species == Species.GERANIUM:
                green = True
            elif neighbor.variety.species == Species.BEGONIA:
                blue = True

        return red and blue and green

    def cultivate_garden(self) -> None:
        VL = copy.copy(self.varieties)
        random.shuffle(VL)

        self.plant_random_from_corner(VL)

        done = False
        while not done:
            done = True
            newPlant = []
            for plant in self.garden.plants:
                if self.has_RBG_neighbors(plant):
                    newPlant.append(plant)
                else:
                    self.delete_plant(plant)
                    done = False
            self.plants = newPlant
