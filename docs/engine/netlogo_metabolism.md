# NetLogo Metabolism Reference

Reference document for the NetLogo (Jayatilake) metabolism implementation.
Used to calibrate the Python coupled diffusion solver.

## Diffusion Parameters

From `diffusion-parameters.txt`:

| Substance | Init (mM) | BC (mM)  | D (m²/s)   | Consumption (mol/s/cell) | Production (mol/s/cell) |
|-----------|-----------|----------|------------|--------------------------|-------------------------|
| Oxygen    | 0.07      | 0.07     | 1.0e-9     | 3.0e-17                  | 0.0                     |
| Glucose   | 5.00      | 5.00     | 6.70e-11   | 3.0e-15                  | 0.0                     |
| Lactate   | 5.00      | 1.00     | 6.70e-11   | 0.0                      | 3.0e-15                 |
| H (protons)| 4e-5     | 4e-5     | 1.0e-9     | 3.0e-15                  | 2.0e-20                 |

## Michaelis-Menten Parameters

From the NetLogo model source:

| Parameter              | NetLogo name            | Value   | Unit |
|------------------------|-------------------------|---------|------|
| Oxygen Vmax            | item 3 (consumption)    | 3.0e-17 | mol/s/cell |
| Oxygen Km (KO2)        | `the-optimal-oxygen`    | 0.005   | mM   |
| Glucose Vmax           | item 3 (consumption)    | 3.0e-15 | mol/s/cell |
| Glucose Km (KG)        | —                       | 0.5     | mM   |
| Lactate Km (KL)        | —                       | 1.0     | mM   |
| Max ATP                | `max-atp`               | 30.0    | —    |
| Proton coefficient     | `proton-coefficient`    | 0.01    | —    |

## Metabolism Formulas

### Michaelis-Menten kinetics

```
MM(S, Km) = S / (Km + S)
```

### Oxidative phosphorylation (mitoATP = true)

```
O2_consumption  = Vmax_O2 * MM(O2, KO2)
Glc_consumption = (Vmax_O2 / 6) * MM(Glc, KG) * MM(O2, KO2)
Lac_consumption = (Vmax_O2 * 2 / 6) * MM(Lac, KL) * MM(O2, KO2)
```

### Glycolysis (glycoATP = true)

```
O2_consumption        = Vmax_O2 * the-glyco-oxygen * MM(O2, KO2)
Glc_consumption_glyco = (Vmax_O2 / 6) * (max_atp / 2) * MM(Glc, KG)
Lac_production        = Glc_consumption_glyco * 3
```

> **Note:** O2 consumption and glucose uptake are computed in **separate code sections**
> in the NetLogo model. Oxygen consumption is applied as a sink term in the diffusion
> equation (lines 2769-2848), weighted by `the-glyco-oxygen` (default 0.5) for glycoATP
> cells. Glucose uptake (lines 3159-3160) has **no oxygen Monod term** — this is the
> Warburg effect: glycolytic cells consume glucose independently of oxygen availability.

## Diffusion Scheme

### NetLogo approach
- **Explicit Euler**, one small timestep per tick
- Timestep: `dt = 0.1 * dx² / D_max` (CFL-like stability condition)
- Consumption applied incrementally each tick
- Inherently stable: small steps prevent overshoot

### Python coupled solver approach
- Solves to **full steady state** in one shot (FiPy PDE solver)
- Faster but can produce negative concentrations if consumption > supply
- Requires Picard iteration + under-relaxation + clamping for stability

## Key Differences (Python vs NetLogo)

| Aspect               | NetLogo           | Python (coupled solver)          |
|----------------------|-------------------|----------------------------------|
| Diffusion solve      | Explicit Euler    | Steady-state (FiPy)             |
| Timestep per tick    | ~0.1 * dx²/D     | Full convergence                 |
| Stability            | Inherent (CFL)    | Picard iteration + relaxation    |
| Negative handling    | Naturally avoided  | Clamping required               |
| O2 Vmax default      | 3.0e-17           | 3.0e-17 (corrected)             |
| KO2 default          | 0.005             | 0.005 (corrected)               |

## Notes on `uptake_rate` in YAML config

The `uptake_rate` defined per substance in the YAML config is stored in `SubstanceConfig`
but **not used by the coupled solver**. The coupled solver computes its own rates in
`_recalculate_metabolism()` using `custom_parameters` (`oxygen_vmax`, `KO2`, etc.).
The YAML `uptake_rate` is only used as a fallback for cells loaded from CSV without
gene networks.
