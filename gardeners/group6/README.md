# Group 6 Gardener

This directory contains the implementation for Group 6's gardener agent, which uses a force-directed layout algorithm to strategically place plants in the garden.

## Algorithm Pipeline

The `cultivate_garden` method in `gardener.py` orchestrates the following steps:

1. **Scatter Seeds** (`scatter_seeds_randomly`): Places 2-3x more plants than available varieties to maximize garden utilization.
2. **Create Beneficial Interactions** (`create_beneficial_interactions`): Uses attractive forces to pull cross-species plants into optimal interaction range.
3. **Separate Overlapping Plants** (`separate_overlapping_plants`): Uses gentle repulsive forces to resolve only hard constraint violations.
4. **Multi-Start Selection**: Runs the above pipeline multiple times and selects the best layout based on a `measure_garden_quality` score.

## Key Features

- **Dynamic Scaling**: Adjusts iterations and parameters based on nursery size
- **Space Optimization**: Scatters more plants than varieties to fill empty garden space
- **Smart Force Order**: Prioritizes beneficial interactions before gentle separation
- **Species Diversity**: Ensures representative sampling from all available species

## Files

- `gardener.py` - Main gardener class with dynamic scaling
- `force_layout.py` - Core force-directed algorithms
- `seed.py` - Random position utilities
- `test_gardener.py` - Test suite
- `config/fruits_and_veggies.json` - Plant varieties configuration

## Usage

```bash
# Run the algorithm
uv run --with numpy python main.py --gardener g6 --json_path gardeners/group6/config/fruits_and_veggies.json --turns 100

# With GUI visualization
uv run --with numpy --with pygame python main.py --gardener g6 --json_path gardeners/group6/config/fruits_and_veggies.json --turns 100 --gui
```

## Performance

- **Time limit**: 60 seconds
- **Multi-start**: 2-12 seeds (scales with problem size)
- **Iterations**: 50-300 (separate) + 100-400 (optimize) - scales dynamically
- **Plant placement**: 2-3x more plants than baseline
- **Growth improvement**: 300-400+ (vs ~30 random baseline)
- **Typical results**: 15-20 plants placed, 300-400+ growth on large configs