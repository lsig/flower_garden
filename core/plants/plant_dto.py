from dataclasses import dataclass

from core.micronutrients import Micronutrient
from core.plants.species import Species


@dataclass(frozen=True)
class PlantDTO:
    name: str
    radius: int
    species: Species
    nutrient_coefficents: dict[Micronutrient, float]
