# Critical Errors in NetLogo Diffusion-Reaction Implementation

**File Analyzed**: `jayathilake2022-main/microC_Metabolic_Symbiosis.nlogo3d`  
**Diffusion Parameters File**: `parameters/diffusion-parameters.txt`  
**Date**: February 12, 2026 (revised)

---

## Executive Summary

The NetLogo implementation of the diffusion-reaction equations contains several
errors that compromise the physical accuracy and numerical validity of the
simulation. This document provides a line-by-line verification of each error
against the actual code and parameter files.

---

## Source Data: Diffusion Parameters

From `parameters/diffusion-parameters.txt`:

| Name    | item 0 (Init.) | item 1 (BC)  | item 2 (Dif.Coef.) | item 3 (Consumption) | item 4 (Production) |
|---------|-----------|---------|------------|-------------|------------|
| Oxygen  | 0.07      | 0.07    | 1.0e-9     | 3.0e-17     | 0.00       |
| Glucose | 5.00      | 5.00    | 6.70e-11   | 3.0e-15     | 0.00       |
| H       | 4e-5      | 4e-5    | 1.0e-9     | 3.0e-15     | 2.0e-20    |
| Lactate | 5.00      | 1.00    | 6.70e-11   | 0.0e-15     | 3.0e-15    |

The code reads these as a list: `[Init., BC, Dif.Coef., Consumption, Production]`
indexed by `item 0`, `item 1`, ..., `item 4`.

---

## Neighbor Topology Verification

Before analyzing the errors, we must understand how many neighbors exist.

The function `sparse-neighbors` (line 529-541) defines the neighbor set:

```netlogo
;; line 536-540
if ( not the-world-3D? )
   [ report patches with [ (abs(pxcor - px) = 2*n+1 and pycor = py)
                         or (pxcor = px and abs(pycor - py) = 2*n+1) ] ]
if ( the-world-3D? )
   [ report patches with [ (abs(pxcor - px) = 2*n+1 and pycor = py and pzcor = pz)
                         or (pxcor = px and abs(pycor - py) = 2*n+1 and pzcor = pz)
                         or (pxcor = px and pycor = py and abs(pzcor - pz) = 2*n+1) ] ]
```

This reports:
- **2D**: 4 face-sharing neighbors (Von Neumann: +x, -x, +y, -y)
- **3D**: 6 face-sharing neighbors (Von Neumann: +x, -x, +y, -y, +z, -z)

This is confirmed and correct. The neighbor topology itself is properly implemented.

---

## Mathematical Reference: Correct Discretization

The equation we want to discretize per substance:

```
∂C/∂t = D ∇²C + R(C)
```

Explicit Euler, finite differences, on a uniform grid with spacing dx:

```
C_new = C_old + α · Σ_neighbors(C_j) - N·α · C_old + dt · R(C_old)
      = (1 - N·α) · C_old + α · Σ_neighbors(C_j) + dt · R(C_old)
```

Where:
- `α = D·dt / dx²` (the numerical Fourier number)
- `N` = number of neighbors (4 in 2D, 6 in 3D)
- `(1 - N·α)` is the "dc-factor"

Stability requires: `N·α ≤ 1`, i.e. `α ≤ 1/N`.

---

## Error #1: Diffusion Coefficient Cancels Out (CONFIRMED)

### Location
Lines 2095-2098, procedure `-NUMERICAL-COEFFICIENTS-3`

### Relevant Code (verbatim)

```netlogo
;; line 2092-2098
set the-dt
    ifelse-value ( biggest-dc > 0 ) [ ( 0.1 * the-dx ^ 2 ) / biggest-dc ] [ 1 ]

foreach ( the-substances )
    [ if ( ? = fastest-diffusing-substance ) [ table:put the-numerical-dc ? 0.1 ]
      if ( ? != fastest-diffusing-substance ) [ table:put the-numerical-dc ?
          ( 1e-9 / item 2 ( table:get the-table-of-diffusion-parameters ? ) )
          * the-dt
          * item 2 ( table:get the-table-of-diffusion-parameters ? )
          / the-dx ^ 2
      ] table:put the-numerical-dc-factor ? 1 - ifelse-value ( the-world-3D? ) [ 4 ] [ 4 ] * table:get the-numerical-dc ? ]
```

### Step-by-step Algebraic Verification

Let:
- `D_s` = `item 2(...)` = diffusion coefficient of substance `s`
- `D_max` = `biggest-dc` = diffusion coefficient of the fastest substance

**Time step** (line 2092-2093):
```
the-dt = 0.1 * dx² / D_max
```

This ensures `α_max = D_max * dt / dx² = 0.1`. Correct so far.

**For the fastest substance** (line 2096):
```
α_max = 0.1
```
Directly assigned. Correct.

**For all other substances** (line 2097):
```
α_s = (1e-9 / D_s) * the-dt * D_s / dx²
    = (1e-9 / D_s) * (0.1 * dx² / D_max) * D_s / dx²
    = 1e-9 * 0.1 / D_max
    = 1e-10 / D_max
```

### Conclusion

**The substance-specific diffusion coefficient `D_s` cancels out completely.**
Every non-fastest substance gets the same numerical coefficient `1e-10 / D_max`,
regardless of its physical diffusion coefficient.

### What the code should compute

The correct Fourier number for substance `s` is:
```
α_s = D_s * dt / dx²
    = D_s * (0.1 * dx² / D_max) / dx²
    = 0.1 * D_s / D_max
```

This means the `(1e-9 / D_s)` factor is spurious — it should not be there.

### Concrete Example

Using values from the parameter file:

| Substance | D (m²/s)  | Correct α_s           | Actual (buggy) α_s     |
|-----------|-----------|----------------------|------------------------|
| Oxygen    | 1.0e-9    | 0.1 (assigned)       | 0.1 (assigned)         |
| Glucose   | 6.70e-11  | 0.1 × 6.70e-11 / 1e-9 = **0.0067** | 1e-10 / 1e-9 = **0.1** |
| H         | 1.0e-9    | 0.1 × 1e-9 / 1e-9 = **0.1** | 1e-10 / 1e-9 = **0.1** |
| Lactate   | 6.70e-11  | 0.1 × 6.70e-11 / 1e-9 = **0.0067** | 1e-10 / 1e-9 = **0.1** |

**Impact**: Glucose and Lactate diffuse ~15× too fast.
H and Oxygen happen to be equal here (both D = 1e-9), so the bug does not
affect H in this particular parameter set. But with any other parameters, it would.

### Severity: CRITICAL

---

## Error #2: Wrong Neighbor Count for 3D (CONFIRMED)

### Location
Line 2098, procedure `-NUMERICAL-COEFFICIENTS-3`

### Relevant Code

```netlogo
table:put the-numerical-dc-factor ?
    1 - ifelse-value ( the-world-3D? ) [ 4 ] [ 4 ] * table:get the-numerical-dc ?
```

### Analysis

The `dc-factor` represents `(1 - N · α)` where N is the number of neighbors.

The code uses:
- 2D: N = 4 (correct)
- 3D: N = 4 (**wrong, should be 6**)

Both branches return `4`, making the `ifelse-value` dead code.

Since `sparse-neighbors` (line 538-540) correctly returns **6 neighbors in 3D**,
the Laplacian `sum[C_j] of sparse-neighbor-of-patch` sums over 6 terms, but the
central term subtracts only `4 · α · C_center`.

### Mathematical Impact

The actual update equation becomes (3D case):
```
C_new = (1 - 4α) · C_old + α · Σ_{j=1..6}(C_j) + dt·R
      = C_old + α · (Σ_{j=1..6}(C_j) - 4·C_old) + dt·R
```

The correct equation should be:
```
C_new = C_old + α · (Σ_{j=1..6}(C_j) - 6·C_old) + dt·R
```

The difference is `+2·α·C_old` per time step — a spurious **positive source
term** that injects mass proportional to the local concentration.

### Physical Interpretation

This error means the simulation **creates mass from nothing** at every interior
patch, at a rate of `2·α·C` per diffusion sub-step. This manifests as:
- Concentrations drifting upward over time
- Effective diffusion appearing slower (less spread because the center retains
  too much)
- Mass conservation is violated

### Concrete Example

With α = 0.1 and uniform concentration C₀:
```
Correct:  C_new = C₀ + 0.1·(6·C₀ - 6·C₀) = C₀         (no change, correct)
Buggy:    C_new = C₀ + 0.1·(6·C₀ - 4·C₀) = C₀ + 0.2·C₀ = 1.2·C₀  (WRONG!)
```

A 20% mass increase per iteration, even for a uniform field!

### Correct Implementation

```netlogo
table:put the-numerical-dc-factor ?
    1 - ifelse-value ( the-world-3D? ) [ 6 ] [ 4 ] * table:get the-numerical-dc ?
```

### Severity: CRITICAL

---

## Error #3: Inconsistent Reaction Term Prefactor Across Species (CONFIRMED)

### Locations

**Oxygen** (line 2786-2788):
```netlogo
table:put temp-substances-of-patch ?
    the-numerical-dc-factor_O * C_O
  + the-numerical-dc_O * Σ(C_O_neighbors)
  - (the-dt / 1e12) * R_O * n-cell1 * Monod_O * (1e18 / dx³)
```

**Glucose** (line 3159-3162):
```netlogo
table:put temp-substances-of-patch ?
    the-numerical-dc-factor_G * C_G
  + the-numerical-dc_G * Σ(C_G_neighbors)
  - ((1e-9 / D_?) * the-dt / 1e12) * (R_O / 6) * n-cell1 * Monod_G * Monod_O * (1e18 / dx³)
  - ((1e-9 / D_?) * the-dt / 1e12) * (R_O / 6) * n-cell2 * the-max-atp/2 * Monod_G * (1e18 / dx³)
```

**H** (line 3427-3429):
```netlogo
table:put temp-substances-of-patch ?
    the-numerical-dc-factor_H * C_H
  + the-numerical-dc_H * Σ(C_H_neighbors)
  + ((1e-9 / D_?) * the-dt / 1e12) * (R_O * 2/6) * n-cell3 * proton_coef * max_atp/2 * Monod_G * (1e18 / dx³)
```

**Lactate** (line 3658-3660):
```netlogo
table:put temp-substances-of-patch ?
    the-numerical-dc-factor_L * C_L
  + the-numerical-dc_L * Σ(C_L_neighbors)
  + ((1e-9 / D_?) * the-dt / 1e12) * (R_O * 2/6) * n-cell3 * max_atp/2 * Monod_G * (1e18 / dx³)
```

### Analysis

The reaction term prefactor differs between species:

| Species  | Prefactor for reaction term            |
|----------|----------------------------------------|
| Oxygen   | `(the-dt / 1e12)`                      |
| Glucose  | `((1e-9 / D_?) * the-dt / 1e12)`     |
| H        | `((1e-9 / D_?) * the-dt / 1e12)`     |
| Lactate  | `((1e-9 / D_?) * the-dt / 1e12)`     |

The `?` variable in the `foreach (the-substances)` loop takes the value of the
current substance name. So when processing Glucose, `D_? = D_Glucose = 6.70e-11`.

### Numerical Values

- **Oxygen prefactor**: `dt / 1e12`
- **Glucose prefactor**: `(1e-9 / 6.70e-11) × dt / 1e12 = 14.93 × dt / 1e12`
- **H prefactor**: `(1e-9 / 1.0e-9) × dt / 1e12 = 1.0 × dt / 1e12`
- **Lactate prefactor**: `(1e-9 / 6.70e-11) × dt / 1e12 = 14.93 × dt / 1e12`

So the reaction terms for Glucose and Lactate are multiplied by **~15× more**
than they should be relative to Oxygen.

For H, the factor happens to be 1.0 (because D_H = 1e-9), so **H is not affected
in this particular parameter set**, but would be with different diffusion
coefficients.

### Expected Behavior

All reaction terms should use the same temporal prefactor `dt` (converted to
proper units). The diffusion coefficient `D` should only appear in the diffusion
term (`α = D·dt/dx²`), never in the reaction term.

### Severity: HIGH

---

## Error #4: Glucose/H/Lactate Use Oxygen's Rate Constant (DESIGN DECISION — NOT NECESSARILY AN ERROR)

### Location
Lines 3160, 3428, 3659

### Observation

The code uses `item 3 ( table:get the-table-of-diffusion-parameters "Oxygen" )`
(= 3.0e-17) in the Glucose, H, and Lactate equations, rather than each
substance's own consumption rate.

For Glucose (line 3160):
```netlogo
(item 3 ( table:get the-table-of-diffusion-parameters "Oxygen" ) * 1.0 / 6 )
```

For H (line 3428):
```netlogo
(item 3 ( table:get the-table-of-diffusion-parameters "Oxygen" ) * 2.0 / 6 )
```

### Analysis

This appears to be an intentional **stoichiometric coupling**:

The aerobic respiration reaction is:
```
C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O + ATP
```

So the oxygen consumption rate `q_O2` is related to glucose consumption as:
```
q_Glucose = q_O2 / 6
```

The code computes `R_O * 1.0 / 6` for glucose and `R_O * 2.0 / 6` for H and
Lactate, which could be a deliberate modeling choice to derive all metabolic rates
from a single master rate (oxygen consumption).

**However**, this is redundant with having separate `item 3` values in the
parameter file. The parameter file lists `Glucose` consumption as `3.0e-15`,
which is `100 × R_O`. This suggests the parameter file rates are NOT meant
to be used for the hard-coded substances (Oxygen, Glucose, H, Lactate) — they
are only used in the "Others" generic equation (line 3985-3987).

### Conclusion

**This is likely intentional, not a bug.** The metabolic stoichiometry is
hard-coded via the oxygen rate. The parameter file's `item 3` for Glucose, H,
and Lactate appears to be overridden by the substance-specific code blocks.

### Severity: LOW (design decision, not a clear error)

---

## Error #5: Dead Code When n-cell3 < 0 for H (CONFIRMED)

### Location
Lines 3435-3449

### Relevant Code

```netlogo
;; line 3435-3443
if (n-cell3 < 0) [
  table:put temp-substances-of-patch ? ...
    + ((1e-9 / D_?) * dt / 1e12) * (R_O * 2/6)
      * (0 * the-proton-coefficient * the-max-atp / 2 ) * Monod_H * Monod_O * (1e18 / dx³)
]
```

Note the factor: `0 * the-proton-coefficient * the-max-atp / 2`

### Analysis

The `n-cell3` variable has been replaced with the literal `0`, making the entire
reaction term zero. The H equation in this branch reduces to **pure diffusion
with no reaction**, which seems unintended.

A commented-out version on line 3438-3439 shows the original intent was to use
`n-cell3` here:
```netlogo
;; * (n-cell3 * the-proton-coefficient * the-max-atp / 2 )
```

It appears the developer wanted to handle the case where `n-cell3 < 0` (net
H consumption) but replaced it with zero, effectively disabling H consumption.

### Severity: MEDIUM

---

## Error #6: Stability Margin in 3D (CONFIRMED, LOW RISK)

### Analysis

The code sets `α_max = 0.1` for the fastest diffusing substance.

Stability requires `N·α ≤ 1`:
- **2D** (N=4): `4 × 0.1 = 0.4 ≤ 1` — stable with 60% margin
- **3D** (N=6): `6 × 0.1 = 0.6 ≤ 1` — stable with 40% margin

Both are stable. However, note that **Error #1** makes all substances have
α ≈ 0.1, meaning in 3D we're always at `N·α = 0.6`, which is safe but
not conservative. Once Error #1 is fixed, Glucose and Lactate would have
α ≈ 0.0067, which is very safe.

### Severity: LOW

---

## Summary of Confirmed Errors

| #  | Error Description                           | Lines       | Severity     | Confirmed |
|----|---------------------------------------------|-------------|--------------|-----------|
| 1  | D cancels in α: all substances diffuse same | 2097        | **CRITICAL** | Yes       |
| 2  | 3D uses 4 neighbors instead of 6 in factor  | 2098        | **CRITICAL** | Yes       |
| 3  | Spurious `1e-9/D` in reaction prefactor      | 3160, 3428, 3659 | **HIGH** | Yes  |
| 4  | Oxygen rate used for Glucose/H/Lactate       | 3160, 3428, 3659 | LOW (intentional) | Revised |
| 5  | Dead code: `0 * ...` disables H consumption  | 3442        | **MEDIUM**   | Yes       |
| 6  | Stability margin suboptimal for 3D          | 2096        | LOW          | Yes       |

---

## Corrections

### Fix #1 — Diffusion coefficient (line 2097)

**Replace**:
```netlogo
( 1e-9 / item 2 ( table:get the-table-of-diffusion-parameters ? ) )
* the-dt * item 2 ( table:get the-table-of-diffusion-parameters ? ) / the-dx ^ 2
```

**With**:
```netlogo
the-dt * item 2 ( table:get the-table-of-diffusion-parameters ? ) / the-dx ^ 2
```

### Fix #2 — Neighbor count (line 2098)

**Replace**:
```netlogo
1 - ifelse-value ( the-world-3D? ) [ 4 ] [ 4 ] * table:get the-numerical-dc ?
```

**With**:
```netlogo
1 - ifelse-value ( the-world-3D? ) [ 6 ] [ 4 ] * table:get the-numerical-dc ?
```

### Fix #3 — Reaction term prefactor (lines 3160, 3428, 3659, 3695, 3986-3987)

**Remove** `((1e-9 / item 2 ( table:get the-table-of-diffusion-parameters ? )))` from all reaction terms.

**Replace**:
```netlogo
((( 1e-9 / item 2 ( table:get the-table-of-diffusion-parameters ? ) )) * the-dt / 1e12) * ...
```

**With** (matching the Oxygen convention):
```netlogo
(the-dt / 1e12) * ...
```

### Fix #5 — Dead H consumption (line 3442)

**Replace**:
```netlogo
* (0 * the-proton-coefficient * the-max-atp / 2 )
```

**With** (using absolute value since n-cell3 < 0 in this branch):
```netlogo
* (n-cell3 * the-proton-coefficient * the-max-atp / 2 )
```

Or set to zero explicitly if the intent is truly to disable consumption in
this branch (but then the entire `if` block is unnecessary).

---

## Validation Recommendations

After implementing these fixes:

1. **Uniform field test**: Initialize all patches with the same concentration,
   no cells. After one iteration, concentration should be unchanged everywhere
   (Laplacian of uniform field = 0). With the current bug #2, it would increase
   by 20% per iteration.

2. **Diffusion speed test**: Initialize a single high-concentration patch,
   no cells. Measure how fast the substance spreads. Compare Oxygen vs Glucose.
   Currently they spread at the same rate; after fix, Oxygen should spread
   ~15× faster than Glucose.

3. **Mass conservation test**: Sum total mass of each substance over all patches.
   Should be constant (minus boundary flux) with no cells present. Bug #2
   violates this.

4. **Stoichiometry test**: With cells consuming Oxygen and Glucose aerobically,
   verify the 6:1 O₂:Glucose molar ratio is maintained.
