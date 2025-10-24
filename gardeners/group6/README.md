# Group 6 Force-Directed Layout Algorithm

A force-directed layout algorithm for optimal plant placement in the flower garden simulation.

## Quick Start

```bash
# Run the algorithm
uv run --with numpy --with pygame python main.py --gardener g6 --json_path gardeners/group6/config/fruits_and_veggies.json --turns 100 --gui

# Run the visualizer
uv run --with numpy --with pygame --with tqdm python gardeners/group6/algorithm_visualizer.py
```

## Algorithm Steps

1. **Scatter Seeds** - Random initial positions
2. **Separate Overlapping Plants** - Repulsive forces remove overlaps  
3. **Create Beneficial Interactions** - Attractive forces optimize cross-species interactions
4. **Multi-start Selection** - Run 12 times, pick best result

## Files

- `gardener.py` - Main algorithm entry point
- `force_layout.py` - Core force-directed algorithms
- `algorithm_visualizer.py` - Interactive step-by-step visualizer
- `config/fruits_and_veggies.json` - Plant varieties configuration

## Visualizer Controls

- **SPACE** - Next step / Next frame
- **D** - Debug mode (show plant details)
- **R** - Reset
- **Q** - Quit

## Performance

- **Time limit**: 60 seconds
- **Multi-start**: 12 seeds
- **Iterations**: 100 (separate) + 50 (optimize)
- **Typical score**: 80-100+ (vs ~30 random baseline)