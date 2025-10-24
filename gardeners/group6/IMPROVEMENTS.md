# Group 6 Algorithm Improvements & Ideas

This document outlines potential improvements to the Group 6 gardener algorithm, organized by category and implementation complexity.

## Current Algorithm Pipeline

1. **Scatter**: Random placement with 8x variety count (up to 320 plants)
2. **Attract**: Pull cross-species plants together (no separation enforcement)
3. **Separate**: Gently separate overlapping plants (reduced iterations/force)
4. **Score**: Count cross-species edges + nodes with degree ≥ 2
5. **Multi-start**: Run multiple times, select best score

---

## 🎯 Scoring & Evaluation Improvements

### 1. Nutrient Flow Score (Pre-Simulation Metric)

**Problem**: Current score only counts edges and degrees; ignores whether interactions are actually productive.

**Idea**: Score the layout based on estimated nutrient production/consumption balance before simulation.

**Implementation**:
- Add new function `measure_nutrient_potential()` in `scoring.py`
- For each cross-species edge, compute nutrient flow potential
- Formula: `(producer_capacity - consumer_need) × interaction_strength`
- Example: Rhododendron (produces R) near Geranium (needs R) = high potential
- Weight by both species' nutrient coefficients

**Where**: `algorithms/scoring.py`

**Benefits**:
- Better pre-simulation metric for layout quality
- Guides algorithm toward naturally productive configurations
- Can replace or complement current edge-counting metric

---

### 2. Species Coverage Score Component

**Problem**: Algorithm may create solutions dominated by 1-2 species, missing beneficial interactions.

**Idea**: Add bonus points if all species are represented in cross-species interactions.

**Implementation**:
- Track which species participate in edges
- Add coverage bonus: `score += (coverage_bonus * num_species_interacting / 3)`
- Ensures balanced ecosystem rather than single-species dominance

**Where**: `algorithms/scoring.py` in `measure_garden_quality()`

**Benefits**:
- Encourages diversity
- Prevents pathological solutions (only Rhododendrons)
- Better nutrient cycling with all three species

---

## 🔧 Placement & Layout Improvements

### 3. Two-Phase Placement Strategy

**Problem**: Initial random scattering wastes iterations; tight clusters could fill space more efficiently.

**Idea**: Optimize interaction clusters first, then greedily fill remaining space.

**Implementation**:
- Phase 1: Run full pipeline on ~30% of varieties → create tight, optimized clusters
- Phase 2: Identify remaining "free space" in garden
- Phase 3: Greedily place remaining 70% of varieties in free areas without breaking clusters
- Track "cluster bounds" to avoid expanding Phase 1 clusters

**Where**: New function `two_phase_placement()` in `gardener.py`, called from `cultivate_garden()`

**Pseudocode**:
```python
def two_phase_placement():
    # Phase 1: Optimize core clusters
    phase1_varieties = select_diverse_subset(varieties, 0.3)
    X_clusters, labels_clusters = optimize_clusters(phase1_varieties)
    
    # Phase 2: Fill gaps
    remaining_varieties = [v for v in varieties if v not in phase1_varieties]
    free_space = find_gaps(garden, X_clusters)
    X_remaining = greedily_place(remaining_varieties, free_space, X_clusters)
    
    # Combine and return
    X_final = combine(X_clusters, X_remaining)
```

**Benefits**:
- Better space utilization
- Focused optimization on high-value clusters
- Prevents wasted iterations trying to fit everyone in interaction range

---

### 4. Adaptive Separation Stopping Condition

**Problem**: Fixed iteration limits may over-separate (breaking edges) or under-separate (leaving overlaps).

**Idea**: Stop separation when marginal progress plateaus or all overlaps resolve.

**Implementation**:
- Track overlap count each iteration
- Implement early stopping:
  - If `overlap_count == 0`: Stop (all resolved)
  - If `consecutive_no_improvement > threshold`: Stop (plateau reached)
  - Calculate: "How many overlaps improved this iteration?"
  - If improvement < threshold: Stop

**Where**: `algorithms/separation.py` in `separate_overlapping_plants()`

**Pseudocode**:
```python
def separate_overlapping_plants(...):
    overlap_count_prev = count_overlaps(X)
    consecutive_no_improvement = 0
    
    for iteration in tqdm(range(iters), ...):
        # ... apply forces ...
        
        overlap_count = count_overlaps(X)
        if overlap_count == 0:
            break  # All overlaps resolved
        
        if overlap_count == overlap_count_prev:
            consecutive_no_improvement += 1
            if consecutive_no_improvement > 5:
                break  # Plateau reached
        else:
            consecutive_no_improvement = 0
        
        overlap_count_prev = overlap_count
    
    return X
```

**Benefits**:
- Prevents over-separation that breaks beneficial edges
- Saves iterations when no progress is being made
- More intelligent stopping criterion than fixed iterations

---

## 🚀 Force Layout Refinements

### 5. Attraction Strength Scaling by Nutrient Fit

**Problem**: Some plant pairs are much more beneficial than others; current attraction treats all cross-species pairs equally.

**Idea**: Vary attraction force strength based on nutrient complementarity.

**Implementation**:
- Calculate nutrient fit score for each pair:
  - How well does variety_i's production match variety_j's consumption?
  - Example: Rhododendron (R_coeff=+1.5) near Geranium (R_coeff=-0.7) = good fit
- Scale attraction force magnitude dynamically:
  - `force_magnitude *= (1.0 + nutrient_fit_bonus)`
  - High fit = stronger attraction, lower fit = weaker attraction

**Where**: `algorithms/attraction.py` in `create_beneficial_interactions()`

**Pseudocode**:
```python
# Calculate nutrient fit
r_coeff_i = varieties[labels[i]].nutrient_coefficients[Micronutrient.R]
r_coeff_j = varieties[labels[j]].nutrient_coefficients[Micronutrient.R]
nutrient_fit = abs(r_coeff_i) * abs(r_coeff_j)  # Penalize both-negative
nutrient_bonus = min(nutrient_fit, 1.0)  # Cap at 1.0

force_magnitude = -displacement * 0.3 * damping * (1.0 + nutrient_bonus)
```

**Benefits**:
- Prioritizes high-value interactions
- Faster convergence to beneficial clusters
- Better layout quality through smarter forces

---

## 📊 Multi-Start & Execution Improvements

### 6. Variety Rotation in Multi-Start

**Problem**: Each multi-start run uses same random variety subset; limits exploration.

**Idea**: Each seed uses different variety rotation, ensuring diverse subset coverage.

**Implementation**:
- Instead of random scattering every run, systematically rotate which varieties are attempted
- Seed 0: varieties[0::num_seeds]
- Seed 1: varieties[1::num_seeds]
- Seed N: varieties[N::num_seeds]
- Or: use stratified random sampling per seed

**Where**: `gardener.py` in `cultivate_garden()` multi-start loop

**Benefits**:
- Ensures all varieties are attempted across runs
- No wasted multi-start on same variety combination
- Better space exploration with fixed budget

---

## 💡 Space Utilization Improvements

### 7. Grid-Based Greedy Filling

**Problem**: After multi-start optimization, garden may still have usable empty pockets.

**Idea**: Post-process: scan garden for empty regions and greedily place remaining plants.

**Implementation**:
- After best layout selected, calculate which varieties weren't placed
- Divide garden into 2x2 meter grid cells
- For each empty cell, try placing lowest-maintenance variety (smallest radius)
- Accept if no constraint violations
- Repeat until no more plants fit or no varieties remain

**Where**: `gardener.py` in `_place_plants()` or new `fill_gaps()` function

**Pseudocode**:
```python
def fill_gaps(placed_X, placed_labels, unplaced_varieties):
    grid_size = 2.0  # meters
    attempts = 0
    max_attempts = len(unplaced_varieties) * 10
    
    while attempts < max_attempts and unplaced_varieties:
        # Find random empty cell
        cell_x = random_float(0, 16.0)
        cell_y = random_float(0, 10.0)
        
        # Try placing smallest unplaced variety
        variety = min(unplaced_varieties, key=lambda v: v.radius)
        
        if can_place(cell_x, cell_y, variety, placed_X, placed_labels):
            placed_X = add_position(placed_X, (cell_x, cell_y))
            placed_labels.append(varieties.index(variety))
            unplaced_varieties.remove(variety)
        
        attempts += 1
```

**Benefits**:
- Fills remaining space systematically
- Safety net for underutilized layouts
- Especially useful on large gardens (16x10)

---

## 🎯 Quick Wins (Easy, High-Impact)

These should be implemented first:

| Idea | Effort | Expected Impact | Why First? |
|------|--------|-----------------|-----------|
| **Species Coverage Score** | 🟢 Low | 🟡 Medium | One-line addition to scoring |
| **Nutrient Flow Score** | 🟡 Medium | 🟢 High | Better metric = better optimization |
| **Adaptive Separation** | 🟡 Medium | 🟡 Medium | Prevents over-separation waste |
| **Variety Rotation** | 🟢 Low | 🟡 Medium | Free improvement in multi-start |
| **Attraction Scaling** | 🟡 Medium | 🟢 High | Smarter force allocation |
| **Two-Phase Placement** | 🟡 Medium | 🟡 Medium | Better space utilization |
| **Grid-Based Filling** | 🟡 Medium | 🟡 Medium | Post-processing safety net |

---

## 📋 Recommended Implementation Order

**Phase 1 (This Sprint)**: Core Improvements
1. Add Species Coverage Score bonus (easiest)
2. Implement Nutrient Flow Score (bigger metric improvement)
3. Add Adaptive Separation Stopping (prevents over-separation)
4. Variety Rotation (free improvement)

**Phase 2 (Next)**: Layout Optimization
1. Attraction Strength Scaling by Nutrient Fit
2. Two-Phase Placement Strategy

**Phase 3 (Polish)**: Advanced Features
1. Grid-Based Gap Filling
2. Performance monitoring & tuning

---

## 📝 Notes & Considerations

- All improvements should maintain < 60 second time limit
- Test each improvement independently before combining
- Monitor score progression to ensure improvements help
- Some ideas may conflict (e.g., tight clustering vs. grid filling) - test interactions
- Consider parallelization for multi-start if hitting time limits
