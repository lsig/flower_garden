# Group 6 Algorithm Visualizer

A custom GUI that visualizes each step of our force-directed layout algorithm in real-time!

## 🎯 What It Shows

### Step 1: Scatter Seeds
- Random initial plant positions
- Each species has a different color (Red/Green/Blue)
- Plant names and radius indicators

### Step 2: Separate Overlapping Plants  
- Repulsive forces push overlapping plants apart
- Visual feedback showing constraint violations
- Plants settle into non-overlapping positions

### Step 3: Create Beneficial Interactions
- Attractive forces pull cross-species plants together
- Plants move toward optimal interaction distances
- Balanced degree distribution emerges

### Step 4: Final Layout
- Complete interaction network
- Quality score and statistics
- Ready for simulation

## 🚀 How to Run

### Quick Start
```bash
# Run with default fruits & veggies config
cd gardeners/group6
uv run --with numpy --with pygame python run_visualizer.py

# Run with specific config
uv run --with numpy --with pygame python run_visualizer.py config/firstnursery.json
```

### Alternative: Direct Python
```bash
# From project root
uv run --with numpy --with pygame python gardeners/group6/visualizer.py
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| **SPACE** | Next algorithm step |
| **R** | Reset to beginning |
| **I** | Toggle interaction lines |
| **F** | Toggle force vectors |
| **ESC** | Quit |

## 🎨 Visual Features

### Plant Representation
- **🔴 Red circles**: Rhododendron (produces R, consumes G&B)
- **🟢 Green circles**: Geranium (produces G, consumes R&B)  
- **🔵 Blue circles**: Begonia (produces B, consumes R&G)
- **Circle size**: Proportional to plant radius (1m, 2m, 3m)
- **Plant labels**: Short names for identification

### Interaction Lines
- **Gray lines**: Connect cross-species plants within interaction range
- **Line opacity**: Stronger interactions = darker lines
- **Only cross-species**: Same species don't interact

### Information Panel
- **Current step**: Shows which algorithm phase is active
- **Statistics**: Plant count, quality score, interaction count
- **Species legend**: Color coding explanation
- **Controls**: Keyboard shortcuts reminder

## 🔧 Customization

### Modify Animation Speed
```python
# In visualizer.py, change:
self.animation_speed = 0.1  # seconds per frame
```

### Change Window Size
```python
# In visualizer.py, modify:
visualizer = Group6Visualizer(varieties, width=1600, height=1000)
```

### Add New Configs
1. Create JSON file in `config/` directory
2. Follow the same format as existing configs
3. Run: `python run_visualizer.py config/your_config.json`

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'numpy'"
```bash
# Make sure to use uv with dependencies
uv run --with numpy --with pygame python run_visualizer.py
```

### "pygame not found"
```bash
# Install pygame
uv pip install pygame
```

### Window doesn't appear
- Check if you're running in a headless environment
- Try running from terminal (not IDE)
- Make sure display is available

### Plants overlap in final layout
- This is normal! The algorithm optimizes for interactions, not perfect spacing
- Real gardens have some overlap for beneficial exchanges

## 📊 Understanding the Algorithm

### Why Force-Directed Layout?
- **Physical intuition**: Plants naturally repel when too close, attract when beneficial
- **Balanced optimization**: Simultaneously handles constraints and objectives
- **Scalable**: Works with any number of plants and varieties

### What the Forces Do
- **Repulsive forces**: Prevent root system overlap (constraint satisfaction)
- **Attractive forces**: Create beneficial cross-species interactions (optimization)
- **Degree damping**: Prevent "hub" plants from dominating

### Quality Score
```
score = (# cross-species interactions) + λ × (# plants with ≥2 neighbors)
```
- Higher score = better layout
- Balances total interactions with degree distribution
- Fast pre-simulation evaluation

## 🎓 Educational Value

This visualizer helps you understand:
- How force-directed algorithms work
- The trade-off between constraints and optimization
- Why multi-start improves results
- The importance of interaction topology

Perfect for presentations, debugging, and algorithm development!

## 🔮 Future Enhancements

- Real-time force vector visualization
- Step-by-step animation with pause/play
- Parameter adjustment sliders
- Export layout images
- Comparison with other algorithms

---

**Enjoy exploring the algorithm!** 🌱✨
