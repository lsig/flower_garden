# Greedy Planting Algorithm

A smart plant placement algorithm that maximizes garden growth through strategic positioning and species diversity.

## 🌱 Algorithm Overview

This algorithm places plants one at a time, always choosing the best location and species combination at each step. Think of it as building a garden where each new plant is positioned to create the strongest possible connections with what's already there.

### Key Ideas

**1. Smart First Three Plants**
- **First plant**: Placed at the garden center with the largest radius species (e.g., Rhododendron)
- **Second plant**: Placed horizontally to the right, choosing the next largest radius (e.g., Begonia)
- **Third plant**: Placed to interact with both previous plants, using the smallest radius (e.g., Geranium)

This creates a strong foundation where all three different species can exchange nutrients efficiently.

**2. Interaction-First Placement**
From the fourth plant onwards, each new plant MUST interact with at least two different species. This ensures every plant has access to diverse nutrients through the exchange network.

**3. Geometric Positioning**
The algorithm finds candidate positions using circle intersections:
- Where do two existing plants' interaction zones overlap?
- Where can a new plant touch multiple neighbors?
- These geometric "sweet spots" maximize nutrient exchange potential.

**4. Simulation-Based Scoring**
Before committing to a placement, the algorithm runs a quick simulation:
- Try placing the plant at candidate position
- Run 100 turns of growth simulation
- Calculate total garden growth
- Choose the position/species that gives the best result

**5. Nutrient Balance**
After the first three plants, the algorithm favors species that produce currently underproduced nutrients, keeping the garden ecosystem balanced.

## 🎯 Why This Works

**Diversity Matters**: Three different species in the foundation means all three nutrients (R, G, B) are being produced and exchanged from the start.

**Geometry Creates Efficiency**: By finding intersection points where plants can interact with multiple neighbors, we maximize nutrient flow without wasting space.

**Radius Strategy**: Starting with large-radius plants (which grow slower but have bigger interaction zones) and ending with small-radius plants (which grow faster) creates an optimal balance.

**Simulation Prevents Guesswork**: Instead of relying on heuristics, we actually test each placement to see how well it performs.

## 🚀 How to Use

### Quick Test

```bash
cd /path/to/flower_garden
bash gardeners/group10/greedy_planting_algorithm_1026/test.sh
```

### Run via Competition Interface

```bash
cd /path/to/flower_garden
bash gardeners/group10/test_main.sh
```

### Configuration

Edit `config.yaml` to adjust:
- `T`: Number of simulation turns for scoring (default: 100)
- `epsilon`: Stop if improvement is below this threshold (default: -0.5)
- `angle_samples`: How many positions to test around each plant (default: 12)
- `verbose`: Show placement progress (default: true)

## 📊 Performance

**Typical Results (test.json)**:
- Plants placed: 4-6 (depends on variety availability)
- Placement time: < 1 second
- Final growth: 35-70 (sustainable growth over 100 turns)

**Key Success Factors**:
- All plants maintain active nutrient exchange
- No isolated plants (all interact with 2+ species)
- Balanced nutrient production across R, G, B

## 🧩 Algorithm Steps (Simplified)

1. **Place Plant 1**: Center of garden, largest radius species
2. **Place Plant 2**: Right of Plant 1, second-largest radius, different species
3. **Place Plant 3**: Position to interact with both 1 & 2, smallest radius, third species
4. **Place Plant 4+**: 
   - Find positions where it can interact with 2+ species
   - Test multiple candidate positions via simulation
   - Choose the best performing position/species combo
   - Stop when no more improvements can be made

## 🔍 What Makes It "Greedy"?

At each step, the algorithm makes the **locally optimal choice** (best plant placement right now) without reconsidering previous decisions. While this doesn't guarantee the global optimum, it's:
- Fast (completes in seconds)
- Practical (doesn't need to search the entire solution space)
- Effective (produces high-quality gardens with sustained growth)

## 📝 Technical Details

- **Language**: Python
- **Key constraints**: 
  - First 3 plants must be different species
  - Plant 3+ must interact with 2+ different species
  - Distance rules: `distance >= max(r1, r2)` for placement, `distance < r1 + r2` for interaction
- **Evaluation**: Weighted average of short-term (turns 1-5) and long-term (turns 6-100) growth

## 🎓 Learn More

See `algorithm_description.txt` for the full technical specification.
