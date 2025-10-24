# Group 6 Gardener - Quick Start Guide

## 🚀 Run It Now

```bash
# Basic run
python main.py --gardener g6 --json_path gardeners/group6/config/firstnursery.json --turns 300

# With visualization
python main.py --gardener g6 --json_path gardeners/group6/config/firstnursery.json --turns 300 --gui

# Random varieties
python main.py --gardener g6 --random --count 15 --seed 42 --turns 300
```

## 📊 Expected Results

**firstnursery.json** (300 turns):
- Final Growth: ~80-90
- Plants Placed: 4-5
- Time: ~0.5-0.6s
- **3× better than random baseline**

## 🎯 What It Does

1. **Random Seed**: Try 12 different starting positions
2. **Remove Overlaps**: Push plants apart using repulsive forces
3. **Create Interactions**: Pull cross-species plants together
4. **Pick Best**: Select layout with highest score

## ⚙️ Tune Parameters

Edit `gardeners/group6/gardener.py` lines 30-34:

```python
self.num_seeds = 12        # More = better quality, slower
self.feasible_iters = 300  # More = better overlap removal
self.nutrient_iters = 200  # More = better interactions
self.band_delta = 0.25     # Smaller = tighter interactions
self.degree_cap = 4        # Lower = more balanced
```

## 🧪 Test It

```bash
# Run test suite
PYTHONPATH=. python gardeners/group6/test_gardener.py

# Compare with random
python main.py --gardener g6 --json_path config.json --turns 300
python main.py --gardener gr --json_path config.json --turns 300
```

## 📚 Learn More

- **README.md** - Algorithm overview
- **SUMMARY.md** - Complete summary
- **docs/runbook.md** - Detailed usage guide
- **docs/algorithm_details.md** - Technical deep dive
- **docs/roadmap.md** - Future extensions

## 🐛 Troubleshooting

**"ModuleNotFoundError: No module named 'numpy'"**
```bash
pip install numpy pygame
```

**"Plants still overlap"**
- Increase `feasible_iters` to 400-500

**"Low growth"**
- Decrease `band_delta` to 0.2
- Increase `nutrient_iters` to 300

**"Takes too long"**
- Decrease `num_seeds` to 6-8
- Decrease iteration counts

## 🎓 Key Concepts

**Force-Directed Layout**: Uses physics simulation to find good positions
- Repulsive forces: Separate overlapping plants
- Attractive forces: Pull cross-species plants together
- Multi-start: Try many starting positions, pick best

**Scoring**: Quick evaluation without simulation
- Count cross-species interactions
- Prefer balanced degree distribution

## 📈 Performance

| Garden Size | Time | Quality vs Random |
|-------------|------|-------------------|
| 9 plants | ~0.5s | +180% |
| 15 plants | ~1.5s | Variable |
| 20 plants | ~3s | TBD |

All well within 60s time limit!

## 🔧 Files You Care About

```
gardeners/group6/
├── gardener.py          ← Main implementation (edit parameters here)
├── force_layout.py      ← Core algorithms
├── config/
│   └── firstnursery.json ← Example plant varieties
└── test_gardener.py     ← Test suite
```

## 💡 Quick Tips

1. **Start simple**: Use default parameters first
2. **Visualize**: Run with `--gui` to see what's happening
3. **Compare**: Always test against random baseline
4. **Tune gradually**: Change one parameter at a time
5. **Test thoroughly**: Run on different nursery configs

## 🎯 Next Steps

1. ✅ Get it running (you're here!)
2. ⏳ Test on different nurseries
3. ⏳ Tune parameters for your scenarios
4. ⏳ Add extensions (see roadmap.md)
5. ⏳ Compete in tournaments!

---

**Questions?** Check the docs/ folder or read the code comments.

**Ready to extend?** See `docs/roadmap.md` for next features to add.

**Want details?** Read `docs/algorithm_details.md` for technical deep dive.

