# Greedy Planting Algorithm with Pattern Replication

An advanced plant placement algorithm that not only optimizes individual plant positions but also replicates successful patterns across the garden for maximum efficiency.

## 🌱 Algorithm Overview

This algorithm works in two phases:
1. **Design Phase**: Create a small, highly optimized "starter group" of plants
2. **Replication Phase**: Copy this proven pattern multiple times across the garden

Think of it like designing a perfect garden "tile" and then laying it across your entire space, like wallpaper or floor tiles.

## 🎯 Core Concept: Why Replicate?

**The Problem**: Placing 30 plants individually takes a lot of time and computation. Each plant requires simulating hundreds of combinations.

**The Solution**: Design a small perfect group (e.g., 5 plants), then copy it. If the pattern works well once, it'll work well everywhere!

**The Benefit**: 
- Faster: Design once, copy many times
- Efficient space use: Proven patterns tile naturally
- Scalable: Works for gardens of any size

## 🔧 How It Works

### Phase 1: Build the Starter Group

**Step 1-3: Strategic Foundation**
- **Plant 1**: Garden center, largest radius species (Rhododendron)
- **Plant 2**: Horizontal right, second-largest radius (Begonia)  
- **Plant 3**: Interact with both, smallest radius (Geranium)

**Step 4+: Optimize the Pattern**
- Continue adding plants greedily
- Each must interact with 2+ different species
- Test positions via simulation
- Stop when pattern can't improve further

This creates a compact, highly efficient "starter group" (typically 3-5 plants).

### Phase 2: Transplant to Origin

Move the starter group so its top-left corner sits at position (0, 0). This creates a clean "stamp" that's easy to copy.

### Phase 3: Replicate Across Garden

**Systematic Tiling**:
- Start from top-left corner
- Try placing the pattern at each position
- Move right, then down (like reading a book)
- Place a copy wherever it fits without overlapping existing plants

**Smart Constraints**:
- All plant centers must stay within garden bounds
- Must maintain proper spacing from existing plants
- Each copy uses fresh plant varieties from inventory

This continues until either:
- Garden is full
- No more plant varieties available
- No valid positions remain

## 📊 Example Results

**Input**: 30 varieties (10 Rhododendron, 10 Geranium, 10 Begonia)

**Starter Group**: 3-5 plants in optimized formation

**After Replication**: 15-25 plants covering the garden
- Multiple copies of the proven pattern
- Efficient space utilization
- Consistent nutrient exchange throughout

**Final Growth**: 700-800 over 100 turns (much higher than single-placement strategies)

## 🚀 How to Use

### Quick Test

```bash
cd /path/to/flower_garden
bash gardeners/group10/greedy_algorithm_with_replacement_1027/test.sh
```

### Via Main Interface

```bash
cd /path/to/flower_garden
bash gardeners/group10/test_main.sh
```

### Configuration

Edit `config.yaml`:
- `T`: Simulation turns for placement scoring (default: 100)
- `epsilon`: Stop threshold for starter group (default: -0.5)
- `verbose`: Show placement and replication progress (default: true)

## 🎨 Visual Analogy

Imagine you're tiling a bathroom floor:

1. **Design the Tile**: Create one beautiful, perfectly balanced tile (starter group)
2. **Test the Tile**: Make sure it actually looks good (simulation)
3. **Lay the Tiles**: Place identical tiles across the whole floor (replication)
4. **Fill Gaps**: Handle edges and corners individually (if needed)

This algorithm does the same with plants!

## 🧩 Algorithm Flow

```
START
  ↓
1. Place first 3 plants (strategic foundation)
  ↓
2. Add 4th, 5th... plants greedily until no improvement
  ↓ [Starter group complete: e.g., 5 plants]
  ↓
3. Move group to origin (0,0)
  ↓
4. Try placing copy at position (0,0) → Already there!
  ↓
5. Try placing copy at position (3,0) → Fits! Place it.
  ↓
6. Try placing copy at position (6,0) → Fits! Place it.
  ↓
7. Continue scanning right and down...
  ↓
8. Try position (9,0) → Doesn't fit (boundary)
  ↓
9. Try position (0,5) → Fits! Place it.
  ↓
... continue until garden is full or varieties exhausted ...
  ↓
END (20 plants placed from 30 available)
```

## 🎯 Key Advantages

**1. Speed**: 
- Design once (expensive), copy many times (cheap)
- Much faster than placing 30 plants individually

**2. Quality**:
- Each copy uses the same proven pattern
- Consistent nutrient exchange across the entire garden

**3. Space Efficiency**:
- Patterns tile naturally without gaps
- Maximizes plant density while maintaining interaction zones

**4. Scalability**:
- Works for any garden size
- Works for any number of varieties
- Automatic adaptation to available space

## 🔍 Comparison with Basic Version

| Feature | Basic Greedy | With Replication |
|---------|--------------|------------------|
| Plants placed | 4-6 | 15-25 |
| Placement time | < 1s | < 1s |
| Final growth | 35-70 | 700-800 |
| Strategy | Optimize each placement | Optimize pattern + replicate |
| Best for | Small gardens | Large gardens with many varieties |

## 💡 When to Use This Algorithm

**Use when**:
- You have many duplicate varieties (e.g., 10 of each species)
- Garden size is large relative to plant radii
- You want maximum space utilization

**Use basic version when**:
- Each variety is unique (no duplicates)
- Garden is small or mostly full
- You need absolute per-plant optimization

## 📝 Technical Notes

- **Pattern tracking**: Uses variety signatures to match duplicates
- **Collision detection**: Checks against both existing plants and within-pattern plants
- **Inventory management**: Tracks available varieties and returns unused ones on failed placements
- **Boundary aware**: Only places patterns where all plant centers fit within bounds

## 🎓 Learn More

The core placement logic (Phase 1) is identical to `greedy_planting_algorithm_1026`. The replication system is an additional layer that leverages proven patterns for maximum efficiency.
