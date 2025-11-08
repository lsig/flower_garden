import csv
import multiprocessing as mp
from typing import Any

from tqdm import tqdm

from core.micronutrients import Micronutrient
from core.runner import GameRunner
from core.settings import GARDENERS

TURNS = 5000
CONFIGS = ['examples/example.json', 'examples/resource_limited.json']


def get_plant_info(plants: list[Any]) -> list[dict]:
    """Extract all relevant plant data into a list of dictionaries"""
    info = []
    for plant in plants:
        plant_data = {
            'variety_name': plant.variety.name,
            'species': plant.variety.species.name,
            'radius': plant.variety.radius,
            'size': plant.size,
            'max_size': plant.max_size,
            'reservoir_capacity': plant.reservoir_capacity,
            # Nutrient coefficients from variety
            'coeff_R': plant.variety.nutrient_coefficients[Micronutrient.R],
            'coeff_G': plant.variety.nutrient_coefficients[Micronutrient.G],
            'coeff_B': plant.variety.nutrient_coefficients[Micronutrient.B],
            # Micronutrient inventory
            'inventory_R': plant.micronutrient_inventory[Micronutrient.R],
            'inventory_G': plant.micronutrient_inventory[Micronutrient.G],
            'inventory_B': plant.micronutrient_inventory[Micronutrient.B],
        }
        info.append(plant_data)
    return info


def write_to_csv(filename: str, data: list[tuple[int, str, str, int, float, list]]):
    """Write results to CSV with one row per plant"""
    with open(filename, 'w', newline='') as csvfile:
        header = [
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
        ]

        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()

        for run_id, gardener, config, turn, growth, plant_info in data:
            for plant in plant_info:
                row = {
                    'Run_ID': run_id,
                    'Gardener': gardener,
                    'Config': config,
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
                }
                writer.writerow(row)


def run_simulation(run_id: int, gardener_name: str, config_file: str, queue: mp.Queue):
    runner = GameRunner(varieties_file=config_file, simulation_turns=TURNS)
    engine = runner._setup_engine(GARDENERS[gardener_name])[0]

    for i in range(TURNS):
        engine.run_turn()
        if i % 100 == 0:
            growth = engine.garden.total_growth()
            plant_info = get_plant_info(engine.garden.plants)
            queue.put((run_id, gardener_name, config_file, i, growth, plant_info))

    # Signal completion
    queue.put(('DONE', run_id, gardener_name, config_file))


def main():
    processes = []
    queue = mp.Queue()
    total_runs = len(CONFIGS) * len(GARDENERS)

    # Start all processes with unique run IDs
    run_id = 0
    for config_file in CONFIGS:
        for gardener_name in GARDENERS:
            p = mp.Process(target=run_simulation, args=(run_id, gardener_name, config_file, queue))
            p.start()
            processes.append(p)
            run_id += 1

    results = []
    with tqdm(total=total_runs, desc='Tournament Progress', unit='run') as pbar:
        completed = 0
        while completed < total_runs:
            item = queue.get()
            if item[0] == 'DONE':
                pbar.update(1)
                completed += 1
            else:
                results.append(item)

    # Wait for all processes to finish
    for p in processes:
        p.join()

    write_to_csv('tournament_results.csv', results)


if __name__ == '__main__':
    main()
