# Gene Network Simulators

This directory contains graph-walking gene network simulators that replicate the NetLogo microC model behavior.

## Available Simulators

### 1. `gene_network_netlogo_faithful.py` - Pure Boolean Network

**Use when**: You want deterministic, purely logic-driven gene network behavior.

**Features**:
- All nodes activate deterministically based on Boolean rules
- Input nodes: `active = (value == ON)`
- No cell-to-cell variability
- Faster and simpler
- Good for testing Boolean logic structure

**Example**:
```bash
python gene_network_netlogo_faithful.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    test_simple_inputs.txt \
    --runs 100 --steps 500 --seed 42
```

---

### 2. `gene_network_netlogo_probability.py` - With Probabilistic Inputs

**Use when**: You want to match NetLogo's exact behavior including stochastic input activation.

**Features**:
- GLUT1I and MCT1I use probabilistic activation (Hill function)
- Each cell gets random thresholds that persist throughout simulation
- Creates **cell-to-cell variability**: cells with identical inputs may behave differently
- Matches NetLogo implementation (lines 1298-1321, 1014-1020)
- Slightly slower due to stochastic evaluation

**Probabilistic mechanism**:
```
probability = 0.85 * (1 - 1 / (1 + (concentration / threshold)))
active = (probability > cell_random_value)
```

**Example**:
```bash
python gene_network_netlogo_probability.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    test_simple_inputs.txt \
    --runs 100 --steps 500 --seed 42
```

With `--seed`, you get reproducible randomness: each run uses a different cell random value, but the sequence is deterministic.

---

## Input File Format

For **both scripts**, inputs are specified as:
```
NodeName=ON    # or OFF
```

For **probability script only**, you can also specify concentrations:
```
GLUT1I=0.5     # 50% of maximum concentration
MCT1I=0.8      # 80% of maximum concentration
```
These will be evaluated probabilistically using the Hill function.

---

## Which Script Should I Use?

| Scenario | Recommended Script |
|----------|-------------------|
| Testing Boolean network structure | `gene_network_netlogo_faithful.py` |
| Comparing with NetLogo simulation results | `gene_network_netlogo_probability.py` |
| Studying cell-to-cell variability | `gene_network_netlogo_probability.py` |
| Fast parameter sweeps | `gene_network_netlogo_faithful.py` |
| Reproducing published NetLogo results | `gene_network_netlogo_probability.py` |

---

## Common Options

Both scripts support:

```bash
--runs 100                 # Number of independent simulations
--steps 500                # Graph-walk steps per simulation
--seed 42                  # Random seed for reproducibility
--non-reversible           # Stop at first fate (default: keep updating)
--apply-cell-actions       # Add proliferation/death event layer
--growth-arrest-cycle 3    # Growth arrest countdown duration
--debug-steps              # Print detailed step-by-step execution
```

---

## Output Interpretation

Both scripts produce identical output format:

- **Final Fate Distribution**: What fate each cell ended up with
- **Fate Node Boolean States**: Final ON/OFF state of fate nodes (usually all OFF)
- **Fate Fire Statistics**: How many times each fate was assigned
- **Timing**: When fates first fired during simulation

The key difference: with the probability script, you'll see more variation across runs even with the same input conditions, due to cell-to-cell variability in GLUT1I/MCT1I activation.

---

## Technical Details

### Graph Walking Mechanism (same in both)

1. Start at random Input node
2. Pick ONE random outgoing edge
3. Update target node
4. Route based on node type:
   - Fate node → set fate, reset node, jump to Input
   - Gene/Input → continue from target

### Probabilistic Activation (probability script only)

NetLogo lines 1014-1020: Each cell gets two random values at birth
```netlogo
set my-cell-ran1 random-float 1.0
set my-cell-ran2 random-float 1.0
```

NetLogo lines 1298-1321: Hill function activation
```netlogo
set my-active
    0.85 - 0.85 / (1.0 + ((concentration / threshold)^1.0)) > my-cell-ran-val
```

This creates a sigmoidal dose-response curve with 85% maximum activation probability.

---

## Reference

Based on: **Jayathilake et al. (2022)** - microC_Metabolic_Symbiosis.nlogo3d

Documentation: `docs/netlogo_phenotype_pipeline.md`
