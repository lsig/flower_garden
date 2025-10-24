# Group 6 Gardener

This directory contains the implementation for Group 6's gardener agent, which uses a force-directed layout algorithm to strategically place plants in the garden.

## Algorithm Pipeline

The `cultivate_garden` method in `gardener.py` orchestrates the following steps:

1. **Scatter Seeds** (`scatter_seeds`): Places plants randomly.
2. **Separate Overlapping Plants** (`separate_overlapping_plants`): Uses repulsive forces to remove overlaps.
3. **Create Beneficial Interactions** (`create_beneficial_interactions`): Uses attractive forces to pull cross-species plants into optimal interaction range.
4. **Multi-Start Selection**: Runs the above pipeline multiple times and selects the best layout based on a `measure_garden_quality` score.

## Files

- `gardener.py` - Main gardener class
- `force_layout.py` - Core force-directed algorithms
- `seed.py` - Random position utilities
- `simulator.py` - Custom simulation logic
- `test_gardener.py` - Test suite
- `config/fruits_and_veggies.json` - Plant varieties configuration

## Usage

```bash
# Run the algorithm
uv run --with numpy python main.py --gardener g6 --json_path gardeners/group6/config/fruits_and_veggies.json --turns 100
```

## Performance

- **Time limit**: 60 seconds
- **Multi-start**: 12 seeds
- **Iterations**: 300 (separate) + 200 (optimize)
- **Typical score**: 80-100+ (vs ~30 random baseline)