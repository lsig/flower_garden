# Beam Search Planting Algorithm with Diversity Bonus

## Overview

This algorithm uses **beam search** to find optimal plant placements while maintaining **diversity** among candidate solutions. Unlike greedy algorithms that commit to a single best choice at each step, beam search explores multiple promising paths simultaneously.

## Key Features

### 1. Beam Search Strategy

- **Maintains k candidate solutions** (beam width): Instead of selecting one best placement, keeps the top k partial solutions
- **Parallel exploration**: Evaluates multiple planting strategies simultaneously
- **Better global optimization**: Less likely to get stuck in local optima compared to greedy approaches

### 2. Diversity Bonus

The algorithm encourages diversity among beam states through:

- **Spatial Diversity**: Rewards solutions with different plant positions
- **Compositional Diversity**: Rewards different variety placement orders
- **Prevents Convergence**: Ensures beam explores different regions of the solution space

**Diversity Calculation:**
```
diversity_score = spatial_diversity + compositional_diversity
- Spatial: Average minimum distance between corresponding plants in different beam states
- Compositional: Number of different variety types at same positions
```

### 3. Nutrient-Aware Selection

Like the greedy algorithm, prioritizes varieties that produce deficient nutrients:
- Tracks cumulative nutrient production (R, G, B)
- Prioritizes varieties that produce the lowest nutrient
- Balances nutrient production across the garden

### 4. Geometric Candidate Generation

- **First plant**: Grid-based sampling
- **Subsequent plants**: Geometric positioning using:
  - Circle-circle intersections (multi-interaction points)
  - Tangency positions (single interactions)
  - Offset positions for density

## Algorithm Flow

```
1. Initialize beam with empty garden state
2. For each iteration:
   a. Expand each beam state:
      - Generate candidate positions
      - Try placing each variety at each position
      - Create new states for valid placements
   b. Score all expanded states:
      - Base score: Simulation-based growth prediction
      - Diversity bonus: How different from other beam states
   c. Prune low-scoring states (threshold-based)
   d. Keep top k states (beam width)
3. Return best final state

```

## Configuration Parameters

### Beam Parameters (`beam:`)

- `width: 5`: Number of candidate solutions to maintain
  - Higher = more exploration, slower
  - Lower = faster, more greedy-like
  
- `diversity_weight: 0.3`: Weight for diversity bonus (0-1)
  - 0 = No diversity, pure beam search
  - 1 = Maximum diversity emphasis
  - 0.3 = Balanced exploration/exploitation

- `pruning_threshold: 0.1`: Prune beams with score < best × threshold
  - Prevents keeping very poor solutions
  - Saves computation

### Simulation Parameters (`simulation:`)

- `T: 100`: Number of turns for final evaluation
- `T_placement: 50`: Turns for scoring during placement
- `w_short: 0.5`: Weight for short-term growth (turns 1-5)
- `w_long: 2.0`: Weight for long-term growth (turns 6+)

### Placement Parameters (`placement:`)

- `nutrient_bonus: 2.0`: Bonus for balancing nutrients
- `beta: 1.0`: Weight for individual plant reward

### Geometry Parameters (`geometry:`)

- `grid_samples: 20`: Grid resolution for first plant
- `angle_samples: 16`: Tangency angles per plant
- `max_candidates: 100`: Maximum candidates per beam state
- `max_anchor_pairs: 50`: Maximum plant pairs for CCI generation

### Heuristic Parameters (`heuristic:`)

- `lambda_interact: 1.0`: Weight for interaction density
- `lambda_gap: 0.5`: Weight for gap penalty

## Usage

### Running Tests

```bash
# Basic test
bash gardeners/group10/beam_search_planting_1026/test.sh

# With GUI (if implemented)
bash gardeners/group10/beam_search_planting_1026/test.sh --gui
```

### Using in Code

```python
from core.garden import Garden
from core.nursery import Nursery
from gardeners.group10.beam_search_planting_1026.gardener import BeamSearchGardener

# Load varieties
nursery = Nursery()
varieties = nursery.load_from_file("config/test.json")

# Create garden and gardener
garden = Garden()
gardener = BeamSearchGardener(garden, varieties)

# Run placement
gardener.cultivate_garden()

# garden now contains the optimal placement
```

## Advantages Over Greedy

1. **Global Optimization**: Explores multiple paths, less prone to local optima
2. **Diverse Solutions**: Diversity bonus prevents premature convergence
3. **Better Long-term Planning**: Multiple lookaheads reveal better strategies
4. **Robustness**: Less sensitive to order-dependent decisions

## Trade-offs

1. **Computational Cost**: O(k × n) vs O(n) for greedy
   - k = beam width
   - n = number of plants
   
2. **Memory Usage**: Must store k complete garden states
   
3. **Tuning Complexity**: More hyperparameters to configure

## Performance Characteristics

- **Best for**: Medium-sized problems (6-20 plants)
- **Beam width 3-5**: Good balance of quality and speed
- **Diversity weight 0.2-0.4**: Prevents convergence without sacrificing quality

## Expected Improvements Over Greedy

- **5-15% better growth** on balanced variety sets
- **More spatially diverse layouts**
- **Better connectivity patterns**
- **More robust to difficult variety combinations**

## Files

- `gardener.py`: Main BeamSearchGardener class
- `utils.py`: Helper functions (geometry, scoring, diversity)
- `config.yaml`: Configuration parameters
- `test_runner.py`: Standalone test script
- `test.sh`: Shell script for testing
- `README.md`: This file

## Notes

- Set `diversity_weight: 0.0` to get pure beam search (no diversity)
- Set `width: 1` to get greedy-like behavior (no beam)
- Verbose mode shows beam evolution in detail
- Works with any variety configuration (balanced or unbalanced)

