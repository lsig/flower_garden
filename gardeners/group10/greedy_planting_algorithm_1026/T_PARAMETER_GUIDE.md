# T Parameter Guide: Adaptive Simulation Turns

## Overview

The `T` parameter in `config.yaml` controls how many simulation turns are used during placement scoring. The algorithm now uses **adaptive T** logic:

```
Actual T used = min(command_line_turns, config_T)
```

## How It Works

### Config Setting (Maximum T)
```yaml
simulation:
  T: 1000  # MAXIMUM turns for placement scoring
```

### Three Usage Scenarios

#### 1. Standalone Testing with `test_runner.py` (RECOMMENDED)
```bash
# Explicitly pass --turns to control T
./test_runner.py --config test.json --turns 100

# Result: Uses T=100 for placement scoring
# - Fast placement (shorter simulations)
# - Accurate for 100-turn competitions
```

#### 2. Using Test Scripts
```bash
# Edit test.sh: TURNS=100
./test.sh

# Result: Uses min(100, 1000) = 100
```

#### 3. Main Project Runner `main.py`
```bash
uv run python main.py --json_path test.json --turns 100 --gardener g10

# Result: Uses config T=1000 (simulation_turns not passed by main.py)
# - Slower placement (1000-turn simulations during scoring)
# - More accurate for long-term optimization
# - Adjust config.yaml T for better performance
```

## Performance Impact

| T Value | Placement Time | Use Case |
|---------|---------------|----------|
| T=50 | ~0.1s | Quick testing, short simulations |
| T=100 | ~0.2s | Standard testing, balanced |
| T=200 | ~0.4s | Moderate accuracy |
| T=500 | ~1.0s | High accuracy for long sims |
| T=1000 | ~2.0s | Maximum accuracy |

**Note**: Times are approximate for 6 varieties. Scales with number of plants.

## When to Adjust T

### For Fast Development
```yaml
T: 100  # Quick iterations
```

### For Standard Competitions (100 turns)
```yaml
T: 1000  # Use --turns 100 with test_runner.py
         # Algorithm will use min(100, 1000) = 100
```

### For Long Competitions (500+ turns)
```yaml
T: 1000  # Caps scoring at reasonable limit
```

## Examples

### Example 1: Testing Different Simulation Lengths
```bash
# Test how algorithm performs at different simulation lengths
./test_runner.py --config test.json --turns 50
# Fast placement, optimized for 50 turns

./test_runner.py --config test.json --turns 200
# Moderate placement, optimized for 200 turns

./test_runner.py --config test.json --turns 2000
# Uses T=1000 (capped), reasonable placement time
```

### Example 2: Competition Preparation
```yaml
# Set in config.yaml
T: 1000  # High maximum for flexibility
```

```bash
# Test with expected competition length
./test_runner.py --config test.json --turns 100

# Result: Placement optimized for 100 turns, not 1000
```

### Example 3: Using main.py
If you need faster placement with `main.py`, adjust config:

```yaml
# Option 1: Lower config T
T: 100  # Faster placement, less accurate for long sims

# Option 2: Keep high T, accept slower placement
T: 1000  # Slower but more accurate
```

## Recommended Settings

### Development/Testing
```yaml
T: 1000
debug:
  verbose: true
```
Use `--turns X` with `test_runner.py` to control actual T.

### Competition Submission
```yaml
T: 1000  # Safe maximum
debug:
  verbose: false
```
Algorithm adapts to actual competition length automatically.

### Performance Tuning
If placement is too slow with `main.py`:
```yaml
T: 200  # Lower maximum for faster placement
```

## Technical Details

### Implementation
```python
class GreedyGardener:
    def __init__(self, garden, varieties, simulation_turns=None):
        self.config = self._load_config()
        
        # Apply adaptive T logic
        if simulation_turns is not None:
            self.config['simulation']['T'] = min(
                simulation_turns, 
                self.config['simulation']['T']
            )
```

### Why This Design?

1. **Flexibility**: One config works for any simulation length
2. **Performance**: Shorter T when appropriate
3. **Accuracy**: Longer T when needed
4. **Backward Compatible**: Works without passing simulation_turns

## Troubleshooting

### Problem: Placement takes too long with main.py
**Solution**: Lower config T
```yaml
T: 100  # or 200, depending on expected simulation length
```

### Problem: Poor results in long simulations
**Solution**: Increase config T or use test_runner.py with explicit --turns
```yaml
T: 1000  # Higher cap
```
```bash
./test_runner.py --config test.json --turns 500
```

### Problem: Different results between test methods
**Cause**: Different T values used
- `test_runner.py --turns 100`: Uses T=100
- `main.py --turns 100`: Uses config T (e.g., 1000)

**Solution**: For consistent results, match T to expected simulation length

## Summary

✅ **Best Practice**: 
- Set config `T: 1000` (high maximum)
- Use `test_runner.py --turns X` for testing
- Algorithm automatically uses `min(X, 1000)`
- Fast placement + accurate results

✅ **For main.py**:
- Set config T to expected simulation length
- Or accept slower placement with high T for better long-term optimization

