"""Python port of PhysiBoSS prostate/custom_modules/drug_sensitivity.cpp.

Implements the two-parameter logistic dose-response model used by the
GDSC database (Vis, D.J. et al. Pharmacogenomics 2016, 17(7):691-700),
plus the drug target / half-life tables originally embedded in the C++
translation unit.

All formulas are kept bit-compatible with the native code so that
stochastic drug-inhibition draws produce the same expected inhibition
probability for a given (cell_line, drug, concentration).
"""

from __future__ import annotations

import math
from typing import Dict, Optional


# Drug -> target node name (anti_<target> is the boolean node in the BN).
# Mirrors drug_sensitivity.cpp::drug_targets.
DRUG_TARGETS: Dict[str, str] = {
    "Ipatasertib": "AKT",
    "Afuresertib": "AKT",
    "Afatinib":    "EGFR",
    "Erlotinib":   "EGFR",
    "Ulixertinib": "ERK",
    "Luminespib":  "HSPs",
    "Trametinib":  "MEK1_2",
    "Selumetinib": "MEK1_2",
    "Pictilisib":  "PI3K",
    "Alpelisib":   "PI3K",
    "BIBR1532":    "TERT",
}


# Drug -> half-life (minutes). Mirrors drug_sensitivity.cpp::half_lives.
HALF_LIVES: Dict[str, int] = {
    "Ipatasertib": 2748,
    "Afuresertib": 2448,
    "Afatinib":    2220,
    "Erlotinib":   2172,
    "Ulixertinib": 105,
    "Luminespib":  7200,
    "Trametinib":  5760,
    "Selumetinib": 822,
    "Pictilisib":  1062,
    "Alpelisib":   822,
}


def get_decay_rate(half_life: float) -> float:
    """Convert half-life (minutes) to a decay rate k such that c(t)=c0*exp(-k*t)."""
    return math.log(2.0) / half_life


# -- Concentration <-> dose-response x scale --------------------------------
# Mirrors drug_sensitivity.cpp: x = log2(conc / max_conc) + 9

def get_x_from_conc(x_conc: float, max_conc: float) -> float:
    """Return the GDSC-scaled x for a drug concentration."""
    return (math.log(x_conc / max_conc) / math.log(2.0)) + 9.0


def get_conc_from_x(x: float, max_conc: float) -> float:
    """Inverse of get_x_from_conc."""
    return max_conc * (2.0 ** (x - 9.0))


def get_lx_from_x(x: float, max_conc: float) -> float:
    """Natural log of concentration at a given x."""
    return math.log(get_conc_from_x(x, max_conc))


# -- Two-parameter logistic (GDSC) ------------------------------------------

def get_cell_viability_for_x(x: float, max_conc: float,
                             xmid: float, scale: float) -> float:
    """Two-parameter logistic: y_hat = 1 / (1 + exp((x - xmid) / scale))."""
    return 1.0 / (1.0 + math.exp((x - xmid) / scale))


def get_x_for_cell_viability(xmid: float, scale: float,
                             cell_viability: float) -> float:
    """Inverse logistic: x such that viability(x) = cell_viability."""
    return math.log((1.0 / cell_viability) - 1.0) * scale + xmid


# -- Public lookup ----------------------------------------------------------

def get_cell_viability_for_drug_conc(drug_conc: float,
                                     drug_params: Dict[str, float]) -> float:
    """Compute cell viability from absolute drug concentration + drug params.

    Args:
        drug_conc: local drug concentration (µM, matching XML user-parameters).
        drug_params: dict with keys ``max_conc``, ``xmid``, ``scale`` as parsed
            from <drug>_maxc / _xmid / _scal in the PhysiCell XML.

    Returns:
        Fractional cell viability in [0, 1].
    """
    if drug_conc <= 0.0:
        return 1.0
    max_conc = drug_params["max_conc"]
    xmid = drug_params["xmid"]
    scale = drug_params["scale"]
    x = get_x_from_conc(drug_conc, max_conc)
    return get_cell_viability_for_x(x, max_conc, xmid, scale)


def get_drug_concentration_from_IC(IC_value: str,
                                   drug_params: Dict[str, float]) -> float:
    """Map a label like ``IC50`` / ``IC90`` to the corresponding concentration.

    The native code parses the string: characters [2] and [3] become the
    digits of the inhibition value (e.g. ``IC90`` -> 0.90).
    """
    if len(IC_value) < 4:
        raise ValueError(f"Invalid IC label: {IC_value!r}")
    inhibition_value = float(f"{IC_value[3]}.{IC_value[2]}")
    final_viability = 1.0 - inhibition_value
    x = get_x_for_cell_viability(drug_params["xmid"],
                                 drug_params["scale"],
                                 final_viability)
    return get_conc_from_x(x, drug_params["max_conc"])


def anti_target_node_name(drug_name: str) -> Optional[str]:
    """Return the BN node that the given drug inhibits (e.g. Pictilisib -> anti_PI3K)."""
    target = DRUG_TARGETS.get(drug_name)
    if target is None:
        return None
    return f"anti_{target}"
