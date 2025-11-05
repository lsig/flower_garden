# Gardener1 Algorithm

## Overview

This gardener implements an optimized strategy for placing plants in a flower garden to maximize growth through nutrient exchanges and efficient packing. The algorithm balances two critical objectives:

1. **Exchange Optimization**: Enable cross-species nutrient exchanges for sustainable growth
2. **Dense Packing**: Maximize the number of plants placed in the garden

## Algorithm Phases

### 1. Group Formation (`_find_optimal_groups_dp`)

Plants are organized into optimal groups based on their nutrient production/consumption profiles.

**For Large Sets (>50 varieties):**
- Uses fast **greedy grouping** that:
  - Ensures species diversity (all 3 species when possible)
  - Groups plants by species first, then fills remaining slots with best matches
  - Limits search to first 50 candidates for efficiency

**For Small Sets (≤50 varieties):**
- Uses **limited combinatorial search**:
  - Searches combinations from first 30 candidates
  - Evaluates each group using multi-factor scoring

### 2. Group Evaluation (`_evaluate_group_balance`)

Each group is scored based on:

- **Growth Sufficiency**: Can production sustain growth requirements? (Plants need 2×radius of each nutrient to grow)
- **Nutrient Balance**: Penalizes imbalance across R, G, B nutrients
- **Species Diversity**: Massive bonus (100 points) for having all 3 species (enables exchanges)
- **Exchange Compatibility**: Rewards complementary nutrient needs between species
- **Production Efficiency**: How well production matches consumption needs

**Key Insight**: The algorithm explicitly checks if groups can sustain continuous growth by comparing production to growth requirements (2×radius per nutrient per turn).

### 3. Grid Generation (`_generate_polygonal_grid`)

Creates a hexagonal grid for efficient circular packing:

- **Grid Spacing**: Based on minimum radius (`min_radius + 0.05`)
  - Radius 1 → 1.05 spacing
  - Radius 2 → 2.05 spacing
  - Radius 3 → 3.05 spacing
- **Multi-Resolution**: For mixed plant sizes, adds a finer secondary grid for small plants

**Why Hexagonal?** Hexagonal packing is ~15% more efficient than square grids for circular objects.

### 4. Plant Placement (`_place_group_on_grid`)

Places each group strategically:

**Sorting Strategy:**
- Larger radius plants first (more growth potential)
- Higher production coefficients second

**Position Scoring:**
- **Cross-Species Exchanges** (12× weight): Critical for nutrient cycling
- **Optimal Distance** (2× weight): Prefers 85-95% of max interaction distance
- **Tight Packing** (1.5× weight): Rewards placements at minimum distance (1.0-1.1× ratio)
- **Partner Penalty**: Prevents too many exchange partners (offers are split)

**Dual Scoring System:**
- When exchanges available: Prioritizes exchange optimization
- When no exchanges: Prioritizes tight packing for density

### 5. Group Size Selection

Tests multiple group sizes and selects the best:

- **Small sets (≤12)**: Tests sizes 3-8
- **Medium sets (13-50)**: Tests sizes 3-6
- **Large sets (51-100)**: Tests sizes 3-5
- **Very large sets (>100)**: Tests sizes 3-4 only

Selects configuration with highest total score, ensuring all 3 species are represented.

## Key Design Principles

### 1. Growth Bottleneck Awareness
Plants require **2×radius of EACH nutrient** to grow. The algorithm explicitly checks if production can sustain this requirement for all three nutrients.

### 2. Exchange Network Optimization
- Only different species can exchange
- Offers are split among partners (fewer partners = larger exchanges)
- Optimal interaction distance: 85-95% of max radius sum

### 3. Balanced Nutrient Production
Heavily penalizes imbalance because growth requires all nutrients. A group that produces 10 R, 10 G, but only 1 B cannot grow effectively.

### 4. Scalability
Uses greedy algorithms for large sets (>50 varieties) to complete within the 60-second time limit while maintaining quality.

### 5. Packing Density
Tight grid spacing based on minimum radius allows maximum plant density while respecting minimum distance constraints (`max(r1, r2)`).

## Performance Characteristics

- **Time Complexity**: O(n²) for greedy grouping, O(n·k) for placement
- **Space Complexity**: O(n) for grid positions
- **Scalability**: Handles 300+ varieties efficiently
- **Time Limit**: Completes well under 60 seconds for large sets

## Configuration Adjustments

The algorithm adapts automatically:
- Grid spacing based on minimum radius
- Group size testing based on variety count
- Search space limits based on set size

## Expected Results

- **High Plant Density**: Tight packing maximizes garden capacity
- **Exchange Networks**: Creates exchange hubs with 2-3 optimal partners
- **Sustainable Growth**: Groups balanced for long-term growth
- **Species Diversity**: Ensures all 3 species are present for exchanges

