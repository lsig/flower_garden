from core.plants.plant import Plant
from core.plants.plant_variety import PlantVariety
from core.point import Position


class Garden:
    def __init__(self, width: float = 16.0, height: float = 10.0) -> None:
        self.width = width
        self.height = height
        self.plants: list[Plant] = []

    def _calculate_distance(self, pos1: Position, pos2: Position) -> float:
        dx = pos1.x - pos2.x
        dy = pos1.y - pos2.y
        return (dx**2 + dy**2) ** 0.5

    def within_bounds(self, position: Position) -> bool:
        return 0 <= position.x <= self.width and 0 <= position.y <= self.height

    def can_place_plant(self, variety: PlantVariety, position: Position) -> bool:
        if not self.within_bounds(position):
            return False

        for existing_plant in self.plants:
            distance = self._calculate_distance(position, existing_plant.position)

            if distance < variety.radius:
                return False

        return True

    def add_plant(self, variety: PlantVariety, position: Position) -> Plant | None:
        if not self.can_place_plant(variety, position):
            return None

        plant = Plant(variety=variety, position=position)
        self.plants.append(plant)
        return plant

    def get_interacting_plants(self, plant: Plant) -> list[Plant]:
        interacting = []
        for other_plant in self.plants:
            if other_plant is plant:
                continue

            if plant.variety.species == other_plant.variety.species:
                continue

            distance = self._calculate_distance(plant.position, other_plant.position)
            interaction_distance = plant.variety.radius + other_plant.variety.radius

            if distance < interaction_distance:
                interacting.append(other_plant)

        return interacting

    def get_all_interactions(self) -> list[tuple[Plant, Plant]]:
        interactions = []
        processed = set()

        for plant in self.plants:
            interacting = self.get_interacting_plants(plant)
            for partner in interacting:
                # NOTE: Use frozenset to avoid duplicates (A,B) and (B,A)
                pair = frozenset([id(plant), id(partner)])
                if pair not in processed:
                    processed.add(pair)
                    interactions.append((plant, partner))

        return interactions

    def total_growth(self) -> float:
        return sum(plant.size for plant in self.plants)
