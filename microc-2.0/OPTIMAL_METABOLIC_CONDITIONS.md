# Optimal Input Combinations for Metabolic States

Based on gene network analysis using the standalone simulator with 200 runs and 2000 steps each.

## Summary Table

| Metabolic State | mitoATP | glycoATP | ATP_Production_Rate | Key Input Combination |
|----------------|---------|----------|-------------------|---------------------|
| **OXPHOS Only** | 100% ON | 100% OFF | 100% ON | O2=ON, Glucose=OFF, MCT1=ON |
| **Glycolysis Only** | 100% OFF | 100% ON | 100% ON | O2=OFF, Glucose=ON, MCT1=OFF |
| **Both Pathways** | 99% ON | 100% ON | 100% ON | O2=ON, Glucose=ON, MCT1=OFF |
| **No ATP** | 100% OFF | 100% OFF | 100% OFF | O2=OFF, Glucose=OFF, MCT1=OFF |

## Detailed Input Configurations

### 1. OXPHOS Only (mitoATP=ON, glycoATP=OFF)
**File:** `test_oxphos_only.txt`
```
Oxygen_supply = true
Glucose_supply = false
MCT1_stimulus = true
```
**Key Mechanism:** MCT1 pathway enables lactate uptake → LDHB=ON → glycoATP=OFF

### 2. Glycolysis Only (mitoATP=OFF, glycoATP=ON)
**File:** `test_glyco_only.txt`
```
Oxygen_supply = false
Glucose_supply = true
MCT1_stimulus = false
```
**Key Mechanism:** No oxygen → ETC=OFF → mitoATP=OFF; Glucose available → glycoATP=ON

### 3. Both Pathways (mitoATP=ON, glycoATP=ON)
**File:** `test_both_atp_v2.txt`
```
Oxygen_supply = true
Glucose_supply = true
MCT1_stimulus = false
```
**Key Mechanism:** Both nutrients available, but no MCT1 → LDHB=OFF → both pathways active

### 4. No ATP (mitoATP=OFF, glycoATP=OFF)
**File:** `test_no_atp.txt`
```
Oxygen_supply = false
Glucose_supply = false
MCT1_stimulus = false
```
**Key Mechanism:** No nutrients available → both pathways inactive

## Key Gene Network Insights

### Critical Regulatory Node: LDHB
- **LDHB = MCT1**
- **MCT1 = Oxygen_supply & MCT1_stimulus & !MCT1I**
- **glycoATP = PEP & !LDHB**

When LDHB is ON (via MCT1), it inhibits glycoATP, creating metabolic exclusivity.

### Metabolic Pathway Dependencies

**OXPHOS Pathway:**
```
mitoATP ← ETC ← (TCA & Oxygen_supply) ← AcetylCoA ← (Pyruvate & PDH)
```

**Glycolysis Pathway:**
```
glycoATP ← (PEP & !LDHB) ← PG2 ← ... ← Cell_Glucose ← (GLUT1 & Glucose_supply)
```

### Biological Interpretation

1. **OXPHOS Only**: Represents cells in lactate-rich, glucose-poor environments (like tumor periphery)
2. **Glycolysis Only**: Represents cells in hypoxic, glucose-rich environments (like tumor core)
3. **Both Pathways**: Represents metabolically flexible cells in optimal conditions
4. **No ATP**: Represents starved/dying cells

## Usage in MicroC Simulations

To achieve specific metabolic states in MicroC simulations, set substance concentrations to trigger these input combinations:

- **Oxygen threshold**: 0.022 mM (for Oxygen_supply)
- **Glucose threshold**: 4.0 mM (for Glucose_supply)  
- **Lactate threshold**: 2.0 mM (for MCT1_stimulus)

Example: For OXPHOS-only cells, set high lactate (>2.0 mM), low glucose (<4.0 mM), high oxygen (>0.022 mM).
