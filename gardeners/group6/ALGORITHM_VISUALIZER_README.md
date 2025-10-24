# Group 6 Algorithm Visualizer - Exact GUI Port

## 🎯 What We Built

A **complete port** of the existing project's pygame GUI, adapted to visualize our force-directed layout algorithm step by step.

### ✨ Features

**Exact Same GUI Style:**
- Same colors, fonts, layout as existing visualizer
- Same controls and interaction patterns
- Same debug mode and info panels
- Same species legend and grid

**Algorithm Visualization:**
- **Step 1**: Scatter seeds (random initial positions)
- **Step 2**: Separate overlapping plants (repulsive forces)
- **Step 3**: Create beneficial interactions (attractive forces)
- **Step 4**: Final layout with interaction network

## 🚀 How to Run

### Quick Start
```bash
# Run with default fruits & veggies (20 varieties)
uv run --with numpy --with pygame python gardeners/group6/algorithm_visualizer.py

# Or use the launcher
uv run --with numpy --with pygame python gardeners/group6/run_algorithm_visualizer.py
```

### With Custom Config
```bash
# First nursery with 15 varieties
uv run --with numpy --with pygame python gardeners/group6/run_algorithm_visualizer.py config/firstnursery.json 15

# Fruits & veggies with 25 varieties
uv run --with numpy --with pygame python gardeners/group6/run_algorithm_visualizer.py config/fruits_and_veggies.json 25
```

## 🎮 Controls (Same as Existing GUI)

| Key | Action |
|-----|--------|
| **SPACE** | Next algorithm step |
| **RIGHT** | Step forward (when paused) |
| **D** | Toggle debug mode |
| **R** | Reset algorithm |
| **Q** | Quit |

## 🎨 Visual Features (Exact Same Style)

### Plant Representation
- **🔴 Crimson Red**: Rhododendron (produces R)
- **🟢 Sea Green**: Geranium (produces G)  
- **🔵 Royal Blue**: Begonia (produces B)
- **Circle size**: Proportional to plant radius
- **Root radius**: Dashed circle showing interaction range

### Debug Mode (Press D)
- **Plant details**: Name, radius, coefficients, species
- **Semi-transparent boxes**: Overlay on each plant
- **Same styling**: Identical to existing visualizer

### Info Panel
- **Algorithm status**: Current step and score
- **Statistics**: Plant count, interactions, score
- **Controls**: Keyboard shortcuts
- **Species legend**: Color-coded circles

### Grid & Layout
- **Garden bounds**: 16m × 10m with grid lines
- **Same scaling**: Identical to existing visualizer
- **Same padding**: 80px margins
- **Same fonts**: 36px, 28px, 20px

## 🔧 Technical Implementation

### Ported Components
- **`draw_grid()`** - Exact same grid rendering
- **`draw_plants()`** - Same plant circles and styling
- **`draw_interactions()`** - Same interaction lines
- **`draw_debug_info()`** - Identical debug overlay
- **`draw_info_panel()`** - Same info panel layout
- **`handle_events()`** - Same control handling

### Algorithm Integration
- **Step-by-step progression**: Space/Right to advance
- **Real-time scoring**: Quality score updates
- **Interaction calculation**: Cross-species connections
- **Reset functionality**: Back to beginning

### Performance Optimizations
- **Limited varieties**: Max 20 by default (configurable)
- **Efficient rendering**: Same 60 FPS as existing
- **Memory management**: Proper cleanup

## 📊 Comparison with Existing GUI

| Feature | Existing GUI | Our Algorithm GUI |
|----------|--------------|------------------|
| **Visual Style** | ✅ | ✅ Identical |
| **Colors** | ✅ | ✅ Same species colors |
| **Fonts** | ✅ | ✅ Same font sizes |
| **Layout** | ✅ | ✅ Same padding/scaling |
| **Controls** | ✅ | ✅ Same key bindings |
| **Debug Mode** | ✅ | ✅ Identical overlay |
| **Grid** | ✅ | ✅ Same grid lines |
| **Info Panel** | ✅ | ✅ Same layout |
| **Purpose** | Simulation | Algorithm steps |

## 🎓 Educational Value

This visualizer perfectly demonstrates:
- **Force-directed algorithms** in action
- **Constraint satisfaction** (no overlaps)
- **Optimization** (beneficial interactions)
- **Multi-step progression** with real-time feedback

Perfect for:
- **Presentations** - Professional GUI
- **Debugging** - See each step clearly
- **Learning** - Understand the algorithm
- **Development** - Test different configs

## 🔧 Customization

### Change Max Varieties
```python
# In algorithm_visualizer.py, modify:
varieties = load_varieties_from_config('fruits_and_veggies.json', max_varieties=30)
```

### Different Config Files
```bash
# Use first nursery
python run_algorithm_visualizer.py config/firstnursery.json 15

# Use custom config
python run_algorithm_visualizer.py config/your_config.json 25
```

### Window Size
```python
# In AlgorithmVisualizer.__init__:
visualizer = AlgorithmVisualizer(varieties, width=1600, height=1000)
```

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
# Make sure to use uv with dependencies
uv run --with numpy --with pygame python gardeners/group6/algorithm_visualizer.py
```

### "Too many plants"
```bash
# Reduce max varieties
python run_algorithm_visualizer.py config/fruits_and_veggies.json 15
```

### "Window doesn't appear"
- Check if running in headless environment
- Try from terminal (not IDE)
- Ensure display is available

## 📁 File Structure

```
gardeners/group6/
├── algorithm_visualizer.py      # Main visualizer (exact GUI port)
├── run_algorithm_visualizer.py  # Easy launcher
├── config/
│   ├── firstnursery.json       # Example config
│   └── fruits_and_veggies.json # Fruits & veggies
└── ALGORITHM_VISUALIZER_README.md # This file
```

## 🎯 Key Benefits

1. **Familiar Interface**: Same as existing project GUI
2. **Professional Look**: Identical styling and layout
3. **Educational**: Step-by-step algorithm visualization
4. **Debugging**: Debug mode shows plant details
5. **Flexible**: Works with any config file
6. **Performant**: Limited varieties for smooth rendering

## 🚀 Next Steps

- **Presentations**: Use for algorithm demos
- **Development**: Test different parameters
- **Learning**: Understand force-directed layout
- **Debugging**: See exactly what each step does

---

**Perfect for understanding our algorithm with the exact same professional GUI as the existing project!** 🌱✨
