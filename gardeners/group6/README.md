# Group 6 Gardener: Force-Directed Layout Strategy

## Overview

Our gardener uses a **force-directed graph layout** approach to optimize plant placement. The algorithm treats plants as nodes in a graph and uses physical simulation to find optimal positions that maximize beneficial cross-species interactions while respecting spatial constraints.

## Algorithm Pipeline

### MVP (Minimum Viable Product)

1. **Scatter Seeds** (`scatter_seeds`)
   - Place all plants at random positions in the 16×10m garden
   - Initialize micronutrient inventories to half-full (5×radius per nutrient)

2. **Separate Overlapping Plants** (`separate_overlapping_plants`)
   - Remove all overlaps by applying repulsive forces
   - Ensures `dist(i,j) ≥ max(r_i, r_j)` for all plant pairs
   - Runs for ~300 iterations with periodic jitter to escape local minima

3. **Create Beneficial Interactions** (`create_beneficial_interactions`)
   - Pull cross-species plants toward interaction range (`r_i + r_j - δ`)
   - Dampen pulls for plants with many neighbors (degree ≥ 4)
   - Maintains feasibility constraints throughout
   - Runs for ~200 iterations

4. **Multi-Start Selection**
   - Run pipeline N times (default: 12 seeds)
   - Score each layout with `measure_garden_quality`
   - Select best layout for placement

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_seeds` | 12 | Number of random starting positions to try |
| `feasible_iters` | 300 | Iterations for overlap removal |
| `nutrient_iters` | 200 | Iterations for nutrient-aware layout |
| `band_delta` | 0.25m | Pull plants to `r_i+r_j-δ` (inside interaction range) |
| `degree_cap` | 4 | Dampen pulls when node has ≥4 neighbors |

## Scoring Function

**Garden Quality Score** (pre-simulation):
```
score = (# cross-species edges within r_i+r_j) + λ·(# nodes with degree≥2)
```

Where λ=1.5 by default. This quickly estimates layout quality without running full simulation.

## Files

- `gardener.py` - Main Gardener6 class and pipeline orchestration
- `force_layout.py` - Force-directed layout algorithms and scoring
- `simulator.py` - Custom simulation for evaluation (optional, uses core engine by default)
- `seed.py` - Utility functions for random placement
- `config/` - Predefined nursery configurations

## Usage

```python
from core.runner import GameRunner
from gardeners.group6.gardener import Gardener6

# Run with custom nursery
runner = GameRunner(
    varieties_file='gardeners/group6/config/firstnursery.json',
    simulation_turns=300
)
result = runner.run(Gardener6)

# Run with GUI
runner.run_gui(Gardener6)
```

## Future Extensions

### Implemented in MVP
- ✅ Random seed placement
- ✅ Feasibility forces (overlap removal)
- ✅ Nutrient-aware forces (interaction optimization)
- ✅ Simple graph scoring
- ✅ Multi-start with best selection

### Planned Extensions
- ⏳ Label refinement (swap species/varieties to improve score)
- ⏳ Nutrient-weighted pulls (scale by actual inventory levels)
- ⏳ Flow-based scoring (max-flow on interaction graph)
- ⏳ Graph extension (bounded-degree edge selection + spring embed)
- ⏳ Parallel multi-start (speed up candidate generation)
- ⏳ Adaptive parameters (tune based on nursery characteristics)

## Design Philosophy

The force-directed approach is inspired by graph visualization algorithms but adapted for the unique constraints of the flower garden problem:

1. **Separation of concerns**: Feasibility and optimization are separate phases
2. **Physical intuition**: Forces provide natural way to balance competing objectives
3. **Scalability**: Works with any number/variety of plants
4. **Robustness**: Multi-start provides diversity and avoids local minima
5. **Extensibility**: Easy to add new forces, constraints, or scoring functions

## Performance

- **Placement time**: ~5-15 seconds for 9 plants with 12 seeds (well under 60s limit)
- **Scalability**: O(N²) per iteration, but converges quickly
- **Quality**: Consistently produces valid layouts with good interaction density

## References

- Force-directed graph drawing (Fruchterman-Reingold, Kamada-Kawai)
- Poisson disk sampling for spatial distribution
- Max-flow algorithms for nutrient balance analysis

