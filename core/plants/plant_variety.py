from dataclasses import dataclass

from core.micronutrients import Micronutrient
from core.plants.species import Species


@dataclass(frozen=True)
class PlantVariety:
    name: str
    radius: int
    species: Species
    nutrient_coefficients: dict[Micronutrient, float]
