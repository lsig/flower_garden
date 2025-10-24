# Group 6 Gardener - Documentation Index

## 🎯 Start Here

**New to the project?** → [QUICKSTART.md](QUICKSTART.md)  
**Want the overview?** → [SUMMARY.md](SUMMARY.md)  
**Need to run it?** → [docs/runbook.md](docs/runbook.md)

## 📚 Documentation Structure

### Getting Started (5 min read)
1. **[QUICKSTART.md](QUICKSTART.md)** - Get running in 2 minutes
2. **[SUMMARY.md](SUMMARY.md)** - High-level overview and results
3. **[README.md](README.md)** - Algorithm description and philosophy

### Understanding the Code (15 min read)
4. **[docs/algorithm_details.md](docs/algorithm_details.md)** - Technical deep dive
5. **[docs/data_types.md](docs/data_types.md)** - Data structures reference
6. **[docs/exchange_rules.md](docs/exchange_rules.md)** - Nutrient exchange protocol

### Using the System (10 min read)
7. **[docs/runbook.md](docs/runbook.md)** - Complete usage guide
8. **[docs/parameters.md](docs/parameters.md)** - Parameter tuning guide
9. **[test_gardener.py](test_gardener.py)** - Test suite and examples

### Planning & Development (15 min read)
10. **[docs/roadmap.md](docs/roadmap.md)** - Development plan and extensions
11. **[docs/project-spec.md](docs/project-spec.md)** - Original problem specification

## 🗂️ File Organization

```
gardeners/group6/
│
├── 📄 Core Documentation
│   ├── INDEX.md              ← You are here
│   ├── QUICKSTART.md         ← Start here for new users
│   ├── SUMMARY.md            ← Project overview
│   └── README.md             ← Algorithm description
│
├── 💻 Implementation
│   ├── gardener.py           ← Main Gardener6 class
│   ├── force_layout.py       ← Force-directed algorithms
│   ├── simulator.py          ← Custom simulation (optional)
│   ├── seed.py              ← Random placement utilities
│   └── test_gardener.py      ← Test suite
│
├── ⚙️ Configuration
│   └── config/
│       ├── firstnursery.json  ← Example plant varieties
│       └── secondnursery.json ← Another example
│
└── 📚 Detailed Documentation
    └── docs/
        ├── algorithm_details.md   ← Technical deep dive
        ├── data_types.md          ← Data structures
        ├── exchange_rules.md      ← Nutrient exchange
        ├── parameters.md          ← Parameter tuning
        ├── project-spec.md        ← Problem specification
        ├── roadmap.md             ← Development plan
        └── runbook.md             ← Usage guide
```

## 🎓 Learning Path

### Path 1: Quick User (30 min)
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Run the examples
3. Skim [docs/runbook.md](docs/runbook.md)
4. Modify parameters and experiment

### Path 2: Developer (2 hours)
1. Read [SUMMARY.md](SUMMARY.md)
2. Read [README.md](README.md)
3. Study [docs/algorithm_details.md](docs/algorithm_details.md)
4. Review code in `gardener.py` and `force_layout.py`
5. Read [docs/roadmap.md](docs/roadmap.md) for extensions
6. Run tests and experiment

### Path 3: Deep Dive (4 hours)
1. Read all documentation in order
2. Study implementation line-by-line
3. Run with different configurations
4. Visualize with GUI
5. Implement an extension from roadmap
6. Write additional tests

## 🔍 Quick Reference

### Common Tasks

**Run basic test**
```bash
python main.py --gardener g6 --json_path gardeners/group6/config/firstnursery.json --turns 300
```
→ See [QUICKSTART.md](QUICKSTART.md)

**Tune parameters**
```python
# Edit gardener.py lines 30-34
self.num_seeds = 12
self.feasible_iters = 300
# ...
```
→ See [docs/parameters.md](docs/parameters.md)

**Understand forces**
```
Repulsive: Push overlapping plants apart
Attractive: Pull cross-species plants together
```
→ See [docs/algorithm_details.md](docs/algorithm_details.md)

**Add extension**
```python
# See roadmap.md for ideas
# Start with label refinement (Phase 3)
```
→ See [docs/roadmap.md](docs/roadmap.md)

### Key Concepts

| Concept | Description | Learn More |
|---------|-------------|------------|
| **Force Layout** | Physics simulation for positioning | [README.md](README.md) |
| **Multi-Start** | Try multiple random seeds | [docs/algorithm_details.md](docs/algorithm_details.md) |
| **Simple Score** | Fast layout evaluation | [docs/algorithm_details.md](docs/algorithm_details.md) |
| **Nutrient Exchange** | How plants trade resources | [docs/exchange_rules.md](docs/exchange_rules.md) |
| **Interaction Range** | When plants can exchange | [docs/project-spec.md](docs/project-spec.md) |

## 📊 Performance Summary

| Metric | Value | Source |
|--------|-------|--------|
| Placement Time | 0.5-1.5s | [test_gardener.py](test_gardener.py) |
| vs Random | +180% growth | [SUMMARY.md](SUMMARY.md) |
| Time Limit | < 60s | [docs/runbook.md](docs/runbook.md) |
| Complexity | O(N²) | [docs/algorithm_details.md](docs/algorithm_details.md) |

## 🛠️ Development Status

| Component | Status | Documentation |
|-----------|--------|---------------|
| MVP | ✅ Complete | [SUMMARY.md](SUMMARY.md) |
| Multi-Start | ✅ Complete | [README.md](README.md) |
| Tests | ✅ Complete | [test_gardener.py](test_gardener.py) |
| Label Refinement | ⏳ Planned | [docs/roadmap.md](docs/roadmap.md) |
| Flow Scoring | ⏳ Planned | [docs/roadmap.md](docs/roadmap.md) |
| Parallelization | ⏳ Planned | [docs/roadmap.md](docs/roadmap.md) |

## 🎯 By Role

### I'm a User
→ [QUICKSTART.md](QUICKSTART.md) + [docs/runbook.md](docs/runbook.md)

### I'm a Developer
→ [README.md](README.md) + [docs/algorithm_details.md](docs/algorithm_details.md) + [docs/roadmap.md](docs/roadmap.md)

### I'm a Grader/Reviewer
→ [SUMMARY.md](SUMMARY.md) + [test_gardener.py](test_gardener.py) + [docs/algorithm_details.md](docs/algorithm_details.md)

### I'm a Competitor
→ [README.md](README.md) + [docs/parameters.md](docs/parameters.md) + [docs/roadmap.md](docs/roadmap.md)

## 📞 Support

**Can't get it running?**
→ Check [QUICKSTART.md](QUICKSTART.md) troubleshooting section

**Don't understand the algorithm?**
→ Read [README.md](README.md) then [docs/algorithm_details.md](docs/algorithm_details.md)

**Want to modify it?**
→ See [docs/parameters.md](docs/parameters.md) for tuning, [docs/roadmap.md](docs/roadmap.md) for extensions

**Need examples?**
→ Run [test_gardener.py](test_gardener.py) or check [docs/runbook.md](docs/runbook.md)

## 🚀 Next Steps

1. ✅ **Read this index** (you're done!)
2. ⏳ **Pick your learning path** (above)
3. ⏳ **Run the code** ([QUICKSTART.md](QUICKSTART.md))
4. ⏳ **Experiment** (modify parameters, try different configs)
5. ⏳ **Extend** (implement features from [docs/roadmap.md](docs/roadmap.md))

---

**Last Updated**: October 24, 2025  
**Version**: 1.0.0  
**Status**: MVP Complete ✅

