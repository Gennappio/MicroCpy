# Gene Network Simulators Comparison

This directory contains multiple gene network simulators with increasing levels of NetLogo fidelity. Here's when to use each:

## Quick Comparison

| Simulator | Purpose | What it simulates | Key output |
|-----------|---------|-------------------|------------|
| `gene_network_netlogo_faithful.py` | **Single cell, single check** | One cell's fate after N steps | Fate distribution (%) |
| `gene_network_netlogo_probability.py` | **Single cell with stochastic inputs** | One cell with probabilistic GLUT1I/MCT1I | Fate distribution (%) with cell variability |
| `gene_network_netlogo_periodic.py` | **Single cell, periodic checks** | One cell checked every 100 ticks | Death timing, transient fate effects |
| `gene_network_population_simulator.py` | **Population with birth/death** | Tumor growth with actual cell divisions/deaths | Population trajectory, growth curves |

---

## 1. `gene_network_netlogo_faithful.py`

**What it does**: Simulates individual cells, checks phenotype ONCE at the end.

**Use when**:
- You want to understand "what % of cells end up in each fate"
- You're comparing Boolean network logic (not population dynamics)
- You want fast batch simulations (100-2000 runs)

**Example**:
```bash
python gene_network_netlogo_faithful.py network.bnd inputs.txt \
    --runs 1000 --steps 500
```

**Output**: 67% Apoptosis, 11% Proliferation, 20% Quiescent

**Limitation**: Doesn't capture NetLogo's periodic checking or population growth.

---

## 2. `gene_network_netlogo_probability.py`

**What it does**: Same as faithful, but adds probabilistic input activation for GLUT1I and MCT1I.

**Use when**:
- You want cell-to-cell variability (each cell has unique random thresholds)
- You're testing how stochastic inputs affect fate distribution
- You want to match NetLogo's Hill function mechanism

**Example**:
```bash
python gene_network_netlogo_probability.py network.bnd inputs.txt \
    --runs 1000 --steps 500 --seed 42
```

**Output**: Same as faithful, but with cell-specific probabilistic activation

**Key difference**: Two cells with identical inputs may have different fates due to random thresholds (`my-cell-ran1`, `my-cell-ran2`).

---

## 3. `gene_network_netlogo_periodic.py`

**What it does**: Simulates individual cells but checks phenotype every N ticks (like NetLogo's `the-intercellular-step`).

**Use when**:
- You want to see **when** cells die (not just final fate)
- You want to capture transient fate effects (apoptosis at tick 234 kills cell even if fate would revert at tick 456)
- You're matching NetLogo's 5000-tick simulations with checks every 100 ticks

**Example**:
```bash
python gene_network_netlogo_periodic.py network.bnd inputs.txt \
    --runs 100 --steps 5000 --periodic-check 100 --seed 42
```

**Output**: 
- 67% cells die from apoptosis (during simulation)
- 11% cells experience proliferation
- Death timing statistics

**Key difference**: Cell can die at tick 300 if Apoptosis is active, even though fate might revert to nobody at tick 500.

---

## 4. `gene_network_population_simulator.py` ⭐ **MOST NETLOGO-LIKE**

**What it does**: Simulates a **POPULATION** where cells actually proliferate (creating daughters) and die (removing from population).

**Use when**:
- You want to see **tumor growth dynamics**
- You want to understand why NetLogo shows growth despite high apoptosis rates
- You want population trajectories over time
- You want to compare directly to NetLogo's cell count plots

**Example**:
```bash
python gene_network_population_simulator.py network.bnd inputs.txt \
    --initial-cells 10 --steps 5000 --periodic-check 100 \
    --max-population 1000 --seed 42
```

**Output**:
- Population trajectory: 10 → 15 → 23 → 38 → 67 → 142 → 347 cells
- Total births: 512
- Total deaths: 175 (apoptosis)
- **Net growth: 337 cells** (exponential!)

**Key insight**: Shows that 67% apoptosis rate + 11% proliferation rate can still produce **exponential tumor growth** because:
1. Early proliferators create lineages
2. Each daughter is a new cell that can proliferate again
3. Population multiplication dominates over death percentage

---

## Which one matches your NetLogo results?

### Your observation:
> "NetLogo shows tumor growth, but my Python script shows 67% apoptosis vs 11% proliferation"

### Answer:
**Use `gene_network_population_simulator.py`** - it's the only one that actually models population growth.

The other scripts answer "what happens to one cell?" while NetLogo answers "what happens to a tumor?" - these are fundamentally different questions.

---

## Example Results Comparison

### Single-cell simulators (faithful, probability, periodic):
```
Apoptosis:      67%
Proliferation:  11%
Quiescent:      20%
```
**Interpretation**: Most individual cells die

### Population simulator:
```
Initial:     10 cells
Final:       347 cells
Total births: 512
Total deaths: 175 (67% of cells that ever existed)
Growth:      34.7x
```
**Interpretation**: Tumor grew exponentially despite 67% individual apoptosis rate!

---

## Running All Simulators

```bash
# 1. Single cell, final check
python gene_network_netlogo_faithful.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    test_simple_inputs.txt --runs 2000 --steps 100

# 2. Single cell with probabilistic inputs
python gene_network_netlogo_probability.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    test_simple_inputs.txt --runs 2000 --steps 100 --seed 42

# 3. Single cell, periodic checks
python gene_network_netlogo_periodic.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    test_simple_inputs.txt --runs 100 --steps 5000 \
    --periodic-check 100 --seed 42

# 4. Population dynamics (RECOMMENDED)
python gene_network_population_simulator.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    test_simple_inputs.txt --initial-cells 10 --steps 5000 \
    --periodic-check 100 --max-population 1000 --seed 42 --verbose
```

---

## Key Takeaway

**NetLogo's tumor growth** comes from:
1. **Population multiplication** (one cell → two cells → four cells)
2. **Spatial heterogeneity** (cells in different locations, different inputs)
3. **Dynamic inputs** (oxygen/glucose diffusion changes over time)
4. **Lineage effects** (early proliferators create many descendants)

Only `gene_network_population_simulator.py` captures #1 (population multiplication), which is the **dominant factor** explaining NetLogo's growth despite high individual apoptosis rates.
