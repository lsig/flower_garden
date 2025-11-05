# Group 6 Algorithm Improvements & Ideas

This document outlines potential improvements to the Group 6 gardener algorithm.

## Current Algorithm Pipeline

1. **Scatter**: Random placement with 8x variety count (up to 320 plants)
2. **Attract**: Pull cross-species plants together (no separation enforcement)
3. **Separate**: Gently separate overlapping plants (reduced iterations/force)
4. **Score**: Count cross-species edges + nodes with degree ≥ 2
5. **Multi-start**: Run multiple times, select best score

---

## 🎯 Your Ideas (Expanded)

### Idea 1: Balanced Nutrient Pre-Selection

**What**: Current random scattering may create nutrient-imbalanced subsets, limiting growth potential.

**Why**: If the initial scatter happens to select mostly one species or unbalanced nutrient producers, the algorithm wastes iterations trying to compensate. Starting with a diverse, balanced subset converges faster.

**Where**: `scatter_seeds_randomly()` or pre-processing before scatter

**How**:
- Compute nutrient "balance score" for each variety (how well it complements others)
- Cluster varieties by complementary nutrients before random selection
- Seed the initial positions with these balanced clusters

---

### Idea 2: Edge-Preserving Separation

**What**: `separate_overlapping_plants()` may break beneficial cross-species edges while separating.

**Why**: You observed: separated plants end up disconnected from their interaction partners. This happens because repulsive forces don't know about beneficial edges - they just push overlapping plants apart indiscriminately.

**Where**: `separate_overlapping_plants()` in `separation.py`

**How**:
- Track which plant pairs have beneficial interactions BEFORE separation
- When applying repulsive forces, check: "Will this move break an edge?"
- Reduce force magnitude or skip separation for edge-critical pairs
- Or add attractive force penalty if separation breaks edges

---

### Idea 3: Parallel Multi-Start Execution

**What**: Sequential multi-start doesn't utilize multiple cores; 60s time limit underutilized.

**Why**: Running seeds sequentially wastes CPU cores. With parallel execution, you get ~4x speedup on quad-core systems while staying under 60s budget, allowing more seeds or deeper optimization.

**Where**: `cultivate_garden()` main loop

**How**:
- Use `multiprocessing.Pool` to run `num_seeds` in parallel
- Each process runs full pipeline (scatter → attract → separate → score)
- Collect results and return best layout
- Automatic speedup: ~4x on quad-core

---

## 💡 Additional Improvement Ideas

### 1. Nutrient Flow Score (Pre-Simulation Metric)

**What**: Score the layout based on estimated nutrient production/consumption balance before simulation.

**Why**: Current score (edges + degree) ignores whether interactions are actually productive. Touching plants with no complementary nutrients waste space.

**Where**: `algorithms/scoring.py` - add new function or extend `measure_garden_quality()`

**How**: For each edge, compute: (producer_capacity - consumer_need) × interaction_strength

---

### 4. Two-Phase Placement Strategy

**What**: Phase 1 - optimize core interaction clusters; Phase 2 - fill gaps greedily.

**Why**: Initial scattering wastes space; tight clusters converge faster. After optimizing the core, remaining space can be filled systematically.

**Where**: `gardener.py` - modify `cultivate_garden()` or create new helper

**How**:
- Run normal pipeline on ~30% of varieties → create tight clusters
- Calculate "free space" in remaining garden
- Greedily place remaining 70% in free areas

---

### 5. Adaptive Separation Stopping Condition

**What**: Stop separating when: (a) no overlaps remain OR (b) marginal benefit plateaus.

**Why**: Fixed iterations may over-separate (breaking edges) or under-separate (wasting iterations). Stopping intelligently saves time and prevents over-optimization.

**Where**: `algorithms/separation.py` in `separate_overlapping_plants()` loop

**How**:
- Count overlaps at each iteration
- Stop if overlap_count reaches zero
- Stop if overlap_count doesn't improve for N consecutive iterations (plateau)

---

### 6. Nutrient-Aware Initial Scattering

**What**: Don't just scatter randomly; cluster by complementary nutrients at start.

**Why**: Random scattering wastes iterations bringing nutrients together. Pre-positioning by nutrient type reduces optimization work.

**Where**: `algorithms/scatter.py` in `scatter_seeds_randomly()`

**How**:
- Group varieties by species (R-producers, G-producers, B-producers)
- Position species clusters near each other initially
- Add random jitter for diversity

---

### 7. Repulsion Force Scaling by Radius Difference

**What**: Plants with very different radii separate more gently (they can coexist).

**Why**: Small plants can fit near large plants - no need to separate aggressively. Large + small = compatible; large + large = threat.

**Where**: `algorithms/separation.py` in `separate_overlapping_plants()`

**How**: Scale `force_magnitude` by radius similarity: `force_magnitude *= (1.0 - abs(r_i - r_j) / (r_i + r_j))`

---

### 8. Jitter Strategy Improvement

**What**: Use "smart jitter" toward underutilized regions instead of random jitter.

**Why**: Current jitter is random noise. Directed jitter toward empty spaces helps fill the garden better.

**Where**: `algorithms/separation.py` jitter section

**How**: Add small attractive force toward centroid of sparse regions during jitter

---

### 9. Grid-Based Greedy Filling

**What**: After multi-start, scan garden for empty spots and try placing additional plants.

**Why**: After optimization, may still have usable pockets of space that greedy filling can exploit.

**Where**: `gardener.py` - post-processing in `_place_plants()` or new `fill_gaps()` function

**How**:
- Divide garden into grid cells (2m x 2m blocks)
- For each empty cell, try placing lowest-maintenance variety (smallest radius)
- Accept if no constraint violations; repeat until full

---

### 10. Density-Based Repulsion Annealing

**What**: Gradually reduce `step_size_feasible` over iterations (simulated annealing).

**Why**: Early iterations need strong separation; later iterations should fine-tune gently. Annealing prevents over-separation and refining.

**Where**: `algorithms/separation.py` in `separate_overlapping_plants()`

**How**: `current_step_size = step_size * (1.0 - iteration / iters) ** 1.5`

---

### 11. Interaction Path Quality Score

**What**: Measure not just "edges exist" but "how productive are the edges?"

**Why**: Current score treats all edges equally. Some interactions are unbalanced (one plant gets much more benefit than the other).

**Where**: `algorithms/scoring.py` - new function `measure_interaction_quality()`

**How**: For each edge, simulate one exchange step; measure net nutrient flow

---

## 🎯 Quick Wins (Easy, High-Impact)

| Idea | Effort | Expected Impact | Why First? |
|------|--------|-----------------|-----------|
| **Parallel Multi-Start** (Idea 3) | 🟢 Low | 🟢 2-4x speedup | Immediate benefit, biggest ROI |
| **Adaptive Separation** (#5) | 🟡 Medium | 🟡 Medium | Prevents wasted iterations |
| **Nutrient-Aware Scatter** (#6) | 🟡 Medium | 🟢 High | Better initial setup → faster convergence |
| **Edge-Preserving Separation** (Idea 2) | 🟡 Medium | 🟢 High | Directly fixes interaction loss issue |
| **Nutrient Flow Score** (#1) | 🟡 Medium | 🟢 High | Better metric = better optimization |
| **Two-Phase Placement** (#4) | 🟡 Medium | 🟡 Medium | Fills remaining space systematically |
| **Repulsion Scaling** (#7) | 🟢 Low | 🟡 Medium | Small change, decent benefit |
| **Grid-Based Filling** (#9) | 🟡 Medium | 🟡 Medium | Post-processing safety net |
| **Jitter Improvement** (#8) | 🟡 Medium | 🟡 Medium | Better space exploration |
| **Density Annealing** (#10) | 🟡 Medium | 🟡 Medium | Fine-tuning improvement |
| **Quality Score** (#11) | 🟡 Medium | 🟢 High | Better evaluation metric |

---

## 📊 Recommended Implementation Order

**Phase 1 (Highest ROI)**:
1. Parallel Multi-Start (Idea 3) - 4x speedup
2. Adaptive Separation Stopping (#5) - prevents wasted iterations
3. Nutrient-Aware Initial Scatter (#6) - better fundamentals

**Phase 2 (Core Improvements)**:
1. Edge-Preserving Separation (Idea 2) - fixes your observation
2. Nutrient Flow Score (#1) - better metric
3. Two-Phase Placement (#4) - space utilization

**Phase 3 (Polish)**:
1. Repulsion Scaling (#7) - radius-aware separation
2. Grid-Based Filling (#9) - gap filling
3. Jitter Improvement (#8) - better exploration
4. Density Annealing (#10) - fine-tuning
5. Quality Score (#11) - holistic evaluation
