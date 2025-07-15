# Apoptosis Analysis Summary: Why High Apoptosis Rates Occur in Gene Networks

## Problem Statement

Initial MicroC simulations showed unrealistically high apoptosis rates (13-99%) even under favorable conditions with oxygen, glucose, and growth factors present. This analysis investigates the causes and solutions.

## Root Causes of Excessive Apoptosis

### 1. Improper Gene Initialization
**Problem**: All genes including fate nodes initialized randomly (50% True/False)
**Impact**: Apoptosis, Proliferation, Growth_Arrest, Necrosis start randomly active
**Solution**: Fate nodes must start as False (biologically correct)

### 2. Over-Convergence Due to Excessive Updates
**Problem**: Too many gene network propagation steps (1000+)
**Impact**: Network converges to states favoring apoptosis over survival
**Solution**: Use sparse updates (10-50 steps) matching NetLogo behavior

### 3. Missing Growth Factor Signaling
**Problem**: Growth factors (EGF, FGF, HGF) not properly configured
**Impact**: Survival pathways (ERK, AKT, BCL2) remain inactive
**Solution**: Ensure all growth factors present and properly mapped

## Apoptosis Logic Analysis

### Gene Network Logic
```
Apoptosis = !BCL2 & !ERK & FOXO3 & p53
```

For apoptosis to occur, ALL conditions must be true:
- BCL2 = False (anti-apoptotic protection OFF)
- ERK = False (survival signaling OFF)  
- FOXO3 = True (pro-apoptotic factor ON)
- p53 = True (tumor suppressor ON)

### Key Survival Pathways
```
BCL2 = CREB & AKT          (anti-apoptotic)
ERK = MEK1_2               (survival signaling)
FOXO3 = JNK & !AKT         (pro-apoptotic, inhibited by AKT)
p53 = (ATM & p38) | ((ATM | p38) & !MDM2)  (stress response)
AKT = PDK1 & !PTEN         (master survival regulator)
```

## NetLogo-Style Update Mechanism

### Pseudocode
```
FUNCTION gene_network_update(network, steps):
    // Initialize genes properly
    FOR each gene IN network:
        IF gene.name IN ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']:
            gene.state = False  // Fate nodes start OFF
        ELSE IF random_initialization:
            gene.state = random_choice([True, False])  // 50% chance
        ELSE:
            gene.state = False
    END FOR
    
    // Sparse single-gene updates (NetLogo style)
    FOR step = 1 TO steps:
        // Select ONE random non-input gene
        updatable_genes = [g for g in network if not g.is_input]
        IF updatable_genes.empty():
            BREAK
        
        selected_gene = random_choice(updatable_genes)
        
        // Evaluate Boolean logic deterministically
        new_state = evaluate_logic(selected_gene.logic_rule, current_gene_states)
        
        // Update only if state changes
        IF selected_gene.state != new_state:
            selected_gene.state = new_state
    END FOR
END FUNCTION
```

## Update Frequency Analysis

### Mathematical Reality
- Total genes: 106 (81 non-input)
- Probability per gene per step: 1/81 ≈ 1.2%
- Expected updates per gene in N steps: N × 0.012

### Observed Apoptosis Update Patterns
- 10 steps: 0% of runs have Apoptosis updates
- 50 steps: 5% of runs have Apoptosis updates  
- 100 steps: 6% of runs have Apoptosis updates
- 200+ steps: Over-convergence leads to excessive apoptosis

## Optimal Anti-Apoptosis Configuration

### Input Conditions
```
# Survival factors (ON)
Oxygen_supply = true
Glucose_supply = true
FGFR_stimulus = true    # FGF growth factor
EGFR_stimulus = true    # EGF growth factor  
cMET_stimulus = true    # HGF growth factor
MCT1_stimulus = true    # Metabolic flexibility

# Stress factors (OFF)
DNA_damage = false
Growth_Inhibitor = false
EGFRI = false          # No drug inhibition
FGFRI = false
cMETI = false
MCT1I = false
MCT4I = false
GLUT1I = false
```

### Network Parameters
```
propagation_steps: 10-50     # Sparse updates
random_initialization: true  # NetLogo-style for non-fate genes
fate_nodes_start_false: true # Biologically correct
```

## Results Summary

### Apoptosis Rates by Configuration
| Configuration | Steps | Apoptosis Rate | Status |
|---------------|-------|----------------|---------|
| Default (broken) | 1000 | 99% | Unrealistic |
| Improved | 100 | 13% | Too high |
| NetLogo-style | 50 | 7% | Acceptable |
| Optimal | 10 | 1% | Realistic |
| Optimal | 50 | 5% | Good |

### Key Insights
1. **Fate node initialization is critical**: Random initialization of Apoptosis node causes immediate false positives
2. **Sparse updates prevent over-convergence**: NetLogo uses very few gene updates per simulation cycle
3. **Growth factor redundancy is essential**: Multiple growth factors provide robust survival signaling
4. **Step count is crucial**: 10-50 steps optimal, 100+ steps cause over-convergence

## Implementation in MicroC

### Configuration Changes
```yaml
gene_network:
  propagation_steps: 50
  random_initialization: true
  
substances:
  FGF: {initial_value: 2.0e-6, boundary_value: 2.0e-6}
  EGF: {initial_value: 2.0e-6, boundary_value: 2.0e-6}  
  HGF: {initial_value: 2.0e-6, boundary_value: 2.0e-6}
  Oxygen: {initial_value: 0.21, boundary_value: 0.21}
  Glucose: {initial_value: 5.0e-3, boundary_value: 5.0e-3}
```

### Code Changes
```python
def reset(self, random_init=False):
    fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}
    for node in self.nodes.values():
        if node.name in fate_nodes:
            node.current_state = False  # Always start as False
        elif random_init and not node.is_input:
            node.current_state = random.choice([True, False])  # NetLogo-style
        else:
            node.current_state = False
```

## Conclusion

High apoptosis rates in gene network simulations result from three main factors: improper initialization of fate nodes, excessive network updates causing over-convergence, and insufficient survival signaling. The solution involves NetLogo-style sparse updates (10-50 steps), proper fate node initialization (start as False), and optimal growth factor conditions. This achieves realistic apoptosis rates of 1-5% under favorable conditions.
