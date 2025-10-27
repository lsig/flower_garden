# Greedy Planting Algorithm

A sophisticated greedy algorithm for optimizing plant placement in the flower garden simulation.

## Algorithm Overview

This algorithm iteratively places plants to maximize long-term growth through:

1. **Geometric Candidate Generation**: Uses circle-circle intersections and tangency sampling to find optimal positions
2. **Nutrient Balance**: Prioritizes varieties that balance the nutrient production across R, G, and B
3. **Interaction Optimization**: Focuses on placing plants where they can interact with different species
4. **Simulation-Based Scoring**: Evaluates each placement by running full simulations

## Key Features

- **Multi-phase Candidate Generation**:
  - Grid sampling for first plant
  - Circle-circle intersections for interaction zones
  - Tangency sampling around existing plants
  
- **Smart Variety Selection**:
  - Analyzes current nutrient production balance
  - Prioritizes varieties that produce underproduced nutrients
  - Considers interaction potential with existing plants
  
- **Adaptive Scoring**:
  - Weights short-term (turns 1-5) and long-term (turns 6-T) growth
  - Adds priority bonus for nutrient-balancing varieties
  - Uses plant reward to encourage sustained growth

## Configuration

Edit `config.yaml` to adjust algorithm parameters:

- `T`: Number of simulation turns for scoring (default: 100)
- `w_short`, `w_long`: Weights for short/long-term growth
- `epsilon`: Improvement threshold for stopping
- `beta`: Plant reward weight
- `nutrient_bonus`: Bonus for nutrient balancing
- `grid_samples`: Initial grid resolution
- `angle_samples`: Tangency angles per plant
- `max_candidates`: Maximum candidates to evaluate

## Usage

Run the test script:

```bash
cd /path/to/flower_garden
./gardeners/group10/greedy_planting_algorithm_1026/test.sh
```

Or run directly with Python:

```bash
uv run python gardeners/group10/greedy_planting_algorithm_1026/test_runner.py \
    --config gardeners/group10/config/test.json
```

Add `--gui` flag to enable visualization.

## Algorithm Details

### Placement Process

1. **Initialization**: Load varieties and configuration
2. **Iterative Placement**:
   - Generate candidate positions based on geometry
   - Prioritize varieties by nutrient balance
   - Evaluate each (variety, position) pair via simulation
   - Place best combination if improvement > epsilon
3. **Termination**: Stop when no improvement or no varieties remain

### Candidate Generation Strategies

- **First Plant**: Uniform grid over garden
- **Subsequent Plants**:
  - Circle-circle intersections between interactable plants
  - Tangency sampling at interaction distances
  - Adjacency sampling for tight packing

### Variety Prioritization

Varieties are ranked by:
- Nutrient balance contribution (higher for underproduced nutrients)
- Interaction potential with existing plants
- Radius (slight preference for smaller radii)

## Performance

### Test Results (test.json configuration)

- **Placement time**: 0.37s (well under 60s limit)
- **Plants placed**: 6/6 varieties
- **Growth metrics**:
  - Turn 5: 26.0
  - Turn 50: 34.0  
  - Turn 100: 35.0
  - **Status**: SUSTAINED GROWTH detected
- **Average growth per plant**: 5.83
- **Key success**: Plant 3 achieved 3-way interactions, enabling continuous nutrient exchange

### Algorithm Characteristics

- Typical placement time: < 1 second for small sets, 5-30 seconds for larger sets
- Plants placed: All available varieties (limited by spacing constraints)
- **Sustained growth**: Algorithm successfully targets continuous long-term growth through optimized interaction positioning

## Implementation Notes

- Uses deep garden copying for safe simulation
- Integer position coordinates for consistent placement
- Geometric heuristics for candidate pruning
- Verbose debug mode available in config

