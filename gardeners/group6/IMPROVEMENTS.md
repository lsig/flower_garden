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

**Idea**: Current scoring only counts edges (interactions exist) and node degrees (interaction count). But not all interactions are equally valuable. Two plants can be touching without having complementary nutrients - wasting space. A Rhododendron (produces R, consumes G/B) next to another Rhododendron produces no nutrient exchange. But a Rhododendron next to a Geranium (produces G, consumes R/B) creates a productive cycle. This score rewards layouts where interacting plants actually help each other.

**Implementation**:
- Create new scoring function that checks nutrient coefficients for each pair of interacting plants
- Score pairs based on complementarity (one produces what the other needs)
- Weight by the magnitude of nutrient exchange possible
- Combine with existing edge count score

**Where**: `algorithms/scoring.py` - add new function or extend `measure_garden_quality()`

---

### 2. Species Coverage Score Component

**Idea**: Sometimes the algorithm creates layouts dominated by one species. For example, mostly Rhododendrons with scattered Geraniums - this limits nutrient cycling since you're missing the Begonia production chain. Encouraging all three species to participate in interactions ensures more balanced nutrient flow across the garden ecosystem.

**Implementation**:
- Track which species have cross-species interactions (not just presence)
- Add bonus points proportional to species diversity in the interaction network
- Example: bonus if all 3 species interact, smaller bonus for 2 species

**Where**: `algorithms/scoring.py` in `measure_garden_quality()`

---

## 🔧 Placement & Layout Improvements

### 3. Two-Phase Placement Strategy

**Idea**: The current approach treats all plants equally - scatter everything randomly, then optimize. But this wastes iterations. Some plants are more valuable for interactions than others. By first creating tight, optimized interaction clusters from a diverse subset, then filling remaining space with leftover plants, we use space more efficiently. The clusters are already good; we're just filling gaps instead of constantly trying to fit a large group together.

**Implementation**:
- Select subset of varieties (30%) emphasizing species diversity
- Run full optimization pipeline on just this subset
- Identify remaining empty regions in garden
- Place remaining varieties (70%) in empty space using simple greedy approach

**Where**: `gardener.py` - modify `cultivate_garden()` or create new helper function

---

### 4. Adaptive Separation Stopping Condition

**Idea**: Currently separation runs for a fixed number of iterations. But sometimes there are no overlaps to fix early on (algorithm converges fast), and sometimes the algorithm plateaus - pushing harder doesn't help. By tracking actual progress (overlap count decreasing), we stop when done or when improvement stalls. This frees up iterations that can be used elsewhere, or just ends faster.

**Implementation**:
- Count overlaps at each separation iteration
- Stop immediately if overlap count reaches zero
- Stop if overlap count stops improving for N consecutive iterations (plateau detection)
- No pseudocode needed - straightforward tracking logic

**Where**: `algorithms/separation.py` in `separate_overlapping_plants()` loop

---

## 🚀 Force Layout Refinements

---

## 📊 Multi-Start & Execution Improvements

### 5. Variety Rotation in Multi-Start

**Idea**: Each multi-start seed currently scatter-randomizes the entire variety set independently. There's a chance two seeds end up trying the same combination, wasting that run. By systematically rotating which varieties each seed attempts (seed 0 tries varieties 0,2,4...; seed 1 tries 1,3,5...), we ensure coverage across the variety space and avoid redundant optimization.

**Implementation**:
- Instead of random selection each seed, use deterministic rotation
- Seed N gets varieties[N::num_seeds] (every Nth variety starting at offset N)
- Or use stratified random sampling to ensure even variety distribution

**Where**: `gardener.py` in `cultivate_garden()` before calling `scatter_seeds_randomly()`

---

## 💡 Space Utilization Improvements

### 6. Grid-Based Greedy Filling

**Idea**: After multi-start finds the best layout, the garden still has unused space. Some plants didn't make it into the selected layout. Rather than starting from scratch, we can scan the empty regions and try to place remaining plants in pockets of free space. It's a quick post-processing step that fills gaps without re-optimizing existing clusters.

**Implementation**:
- After selecting best layout, identify which varieties weren't placed
- Divide garden into grid cells (2m x 2m blocks)
- For each empty cell, attempt to place smallest unplaced variety
- Accept if no constraint violations; repeat until space full or plants exhausted

**Where**: `gardener.py` - new `fill_gaps()` function called after `_place_plants()` selects best layout

---

## 🎯 Quick Wins (Easy, High-Impact)

These should be implemented first:

| Idea | Effort | Expected Impact | Why First? |
|------|--------|-----------------|-----------|
| **Species Coverage Score** | 🟢 Low | 🟡 Medium | One-line addition to scoring |
| **Nutrient Flow Score** | 🟡 Medium | 🟢 High | Better metric = better optimization |
| **Adaptive Separation** | 🟡 Medium | 🟡 Medium | Prevents over-separation waste |
| **Variety Rotation** | 🟢 Low | 🟡 Medium | Free improvement in multi-start |
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
1. Two-Phase Placement Strategy

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
