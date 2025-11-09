import csv
from typing import Any

from tqdm import tqdm

from core.micronutrients import Micronutrient
from core.runner import GameRunner
from core.settings import GARDENERS

TURNS = 5000
CONFIGS = [f'examples/config{i}_{j}.json' for i in range(1, 29) for j in range(1, 4)]


def get_plant_info(plants: list[Any]) -> list[dict]:
    info = []
    for plant in plants:
        plant_data = {
            'variety_name': plant.variety.name,
            'species': plant.variety.species.name,
            'radius': plant.variety.radius,
            'size': plant.size,
            'max_size': plant.max_size,
            'reservoir_capacity': plant.reservoir_capacity,
            'coeff_R': plant.variety.nutrient_coefficients[Micronutrient.R],
            'coeff_G': plant.variety.nutrient_coefficients[Micronutrient.G],
            'coeff_B': plant.variety.nutrient_coefficients[Micronutrient.B],
            'inventory_R': plant.micronutrient_inventory[Micronutrient.R],
            'inventory_G': plant.micronutrient_inventory[Micronutrient.G],
            'inventory_B': plant.micronutrient_inventory[Micronutrient.B],
        }
        info.append(plant_data)
    return info


def run_simulation(run_id: int, gardener_name: str, config_file: str):
    runner = GameRunner(varieties_file=config_file, simulation_turns=TURNS)
    engine, _, placement_time = runner._setup_engine(GARDENERS[gardener_name])

    for i in range(TURNS):
        engine.run_turn()
        if i % 100 == 0:
            growth = engine.garden.total_growth()
            plant_info = get_plant_info(engine.garden.plants)
            yield (run_id, gardener_name, config_file, i, growth, plant_info, placement_time)


def main():
    total_runs = len(CONFIGS) * len(GARDENERS)
    tasks = [
        (run_id, gardener, config)
        for run_id, (config, gardener) in enumerate((c, g) for c in CONFIGS for g in GARDENERS)
    ]

    fieldnames = [
        'Run_ID',
        'Gardener',
        'Config',
        'Turn',
        'Total_Growth',
        'Variety_Name',
        'Species',
        'Radius',
        'Size',
        'Max_Size',
        'Reservoir_Capacity',
        'Coeff_R',
        'Coeff_G',
        'Coeff_B',
        'Inventory_R',
        'Inventory_G',
        'Inventory_B',
        'Placement_Time',
    ]

    with open('tournament_results.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for run_id, gardener, config in tqdm(tasks, total=total_runs, desc='Tournament Progress'):
            try:
                for turn_data in run_simulation(run_id, gardener, config):
                    run_id, gardener, config_file, turn, growth, plant_info, placement_time = (
                        turn_data
                    )
                    for plant in plant_info:
                        writer.writerow(
                            {
                                'Run_ID': run_id,
                                'Gardener': gardener,
                                'Config': config_file,
                                'Turn': turn,
                                'Total_Growth': growth,
                                'Variety_Name': plant['variety_name'],
                                'Species': plant['species'],
                                'Radius': plant['radius'],
                                'Size': plant['size'],
                                'Max_Size': plant['max_size'],
                                'Reservoir_Capacity': plant['reservoir_capacity'],
                                'Coeff_R': plant['coeff_R'],
                                'Coeff_G': plant['coeff_G'],
                                'Coeff_B': plant['coeff_B'],
                                'Inventory_R': plant['inventory_R'],
                                'Inventory_G': plant['inventory_G'],
                                'Inventory_B': plant['inventory_B'],
                                'Placement_Time': placement_time,
                            }
                        )
            except Exception as e:
                print(f'Run failed: {e}')


if __name__ == '__main__':
    main()
