# Testing Guide for Greedy Planting Algorithm

There are two ways to test the algorithm:

## Option 1: Standalone Testing (`test.sh`)

**Recommended for development and debugging**

```bash
./gardeners/group10/greedy_planting_algorithm_1026/test.sh
```

**Features:**
- Uses standalone `test_runner.py`
- More detailed output and analysis
- Shows growth patterns at turns 5, 50, 100
- Displays per-plant interaction details
- Nutrient balance analysis
- Growth rate analysis

**Configuration:**
- Edit `test.sh` to change:
  - `CONFIG`: Path to JSON file (test.json or easy.json)
  - `GUI_ON`: true/false for GUI visualization
- Edit `config.yaml` for algorithm parameters (T, weights, etc.)

**Best for:**
- Algorithm development
- Debugging placement issues
- Analyzing growth patterns
- Testing different hyperparameters

---

## Option 2: Main Project Runner (`test_main.sh`)

**Recommended for competition and integration testing**

```bash
./gardeners/group10/greedy_planting_algorithm_1026/test_main.sh
```

**Features:**
- Uses official `main.py` interface
- Tests integration with main project
- Same output format as other gardeners
- Official competition mode

**Configuration:**
- Edit `test_main.sh` to change:
  - `CONFIG`: Path to JSON file
  - `TURNS`: Number of simulation turns
  - `GUI_ON`: true/false for GUI

**Best for:**
- Integration testing
- Competition mode
- Comparing with other gardeners
- Final validation

---

## Direct Main.py Usage

You can also run directly using `main.py`:

```bash
# Command line only
uv run python main.py --json_path gardeners/group10/config/test.json --turns 100 --gardener g10

# With GUI
uv run python main.py --json_path gardeners/group10/config/test.json --turns 100 --gardener g10 --gui
```

---

## Quick Comparison

| Feature | test.sh (Standalone) | test_main.sh (Main Runner) |
|---------|---------------------|---------------------------|
| Detailed output | ✅ Full analysis | ❌ Summary only |
| Growth analysis | ✅ Turns 5/50/100 | ❌ Final only |
| Integration test | ❌ | ✅ Official interface |
| Debug mode | ✅ Configurable | ✅ Via config.yaml |
| Per-plant details | ✅ Interactions shown | ❌ |
| Competition format | ❌ | ✅ |

---

## Adaptive Simulation Turns

The algorithm automatically adapts to your simulation length:

**How it works:**
- Config `T: 1000` sets the MAXIMUM turns for scoring during placement
- If you run with `--turns 100`, the algorithm uses `min(100, 1000) = 100` for scoring
- If you run with `--turns 5000`, the algorithm caps at `min(5000, 1000) = 1000`

**Why this matters:**
- **Performance**: Running 1000-turn simulations during placement would be slow
- **Accuracy**: Scoring should match expected simulation length
- **Flexibility**: One config works for any simulation length

**Examples:**
```bash
# Short simulation (50 turns) - fast placement
./test_runner.py --config test.json --turns 50
# Uses T=50 for scoring

# Standard simulation (100 turns) - balanced
./test_runner.py --config test.json --turns 100
# Uses T=100 for scoring

# Long simulation (500 turns) - accurate long-term
./test_runner.py --config test.json --turns 500
# Uses T=500 for scoring (still within max)

# Very long simulation (5000 turns)
./test_runner.py --config test.json --turns 5000
# Uses T=1000 for scoring (capped at config max)
```

---

## Configuration Files

### Test Configurations

**`gardeners/group10/config/test.json`**
- 6 varieties total
- 3 Rhododendron (radius=3)
- 2 Geranium (radius=1)
- 1 Begonia (radius=1)
- Good for quick testing

**`gardeners/group10/config/easy.json`**
- 30 varieties total
- 10 of each species
- Tests scalability
- Longer placement time (~1-2s)

### Algorithm Configuration

**`gardeners/group10/greedy_planting_algorithm_1026/config.yaml`**

Key parameters:
```yaml
simulation:
  T: 1000                  # MAXIMUM turns for placement scoring
                            # Actual T = min(T, simulation_turns)
                            # Set high (1000) to adapt to any simulation length
  w_short: 0.2             # Weight for early growth
  w_long: 1.0              # Weight for late growth

placement:
  epsilon: -0.5            # Stopping threshold
  beta: 1.5                # Plant reward weight
  nutrient_bonus: 3.0      # Nutrient balance bonus

geometry:
  max_candidates: 50       # Max candidates per iteration
  max_anchor_pairs: 15     # Max anchor pairs

debug:
  verbose: true            # Progress output
```

---

## Example Workflows

### Development Workflow
```bash
# 1. Edit config.yaml to test different parameters
vim gardeners/group10/greedy_planting_algorithm_1026/config.yaml

# 2. Run standalone test for detailed output
./gardeners/group10/greedy_planting_algorithm_1026/test.sh

# 3. Analyze results and iterate
```

### Competition Workflow
```bash
# 1. Ensure verbose is false in config.yaml
vim gardeners/group10/greedy_planting_algorithm_1026/config.yaml
# Set: verbose: false

# 2. Test with main runner
./gardeners/group10/greedy_planting_algorithm_1026/test_main.sh

# 3. Verify output format matches competition requirements
```

### GUI Testing Workflow
```bash
# Option 1: Using test.sh
# Edit test.sh: GUI_ON=true
./gardeners/group10/greedy_planting_algorithm_1026/test.sh

# Option 2: Using test_main.sh
# Edit test_main.sh: GUI_ON=true
./gardeners/group10/greedy_planting_algorithm_1026/test_main.sh

# Option 3: Direct
uv run python main.py --json_path gardeners/group10/config/test.json --turns 100 --gardener g10 --gui
```

---

## Expected Results (test.json)

With default configuration:
- **Plants placed**: 5/6 (83%)
- **Final growth**: ~60-70
- **Placement time**: < 0.2s
- **All plants**: Interact with 2+ different species ✅
- **Growth pattern**: Sustained long-term growth

---

## Troubleshooting

### Problem: Placement takes too long
**Solution**: Reduce parameters in `config.yaml`:
- Lower `T` (e.g., 100 → 50)
- Lower `max_candidates` (e.g., 50 → 30)
- Lower `max_anchor_pairs` (e.g., 15 → 10)

### Problem: No growth after placement
**Solution**: Check multi-species interactions:
- All plants (3rd onwards) must interact with 2+ species
- Check debug output for "REJECTED" candidates
- May need more varieties of different species

### Problem: Too much output
**Solution**: Disable verbose in `config.yaml`:
```yaml
debug:
  verbose: false
```

### Problem: Algorithm stops early (few plants)
**Solution**: Check epsilon threshold:
- Lower `epsilon` (e.g., -0.5 → -1.0) to allow more placements
- Or check if constraint is too strict (all candidates rejected)

