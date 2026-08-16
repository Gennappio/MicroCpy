"""
Hill (Probabilistic) Input Activation - mark gene inputs as probabilistic.

This node is the canvas-visible switch for the NetLogo probabilistic drug
activation (microC_Metabolic_Symbiosis.nlogo3d, -ACTIVE-FROM-PATCH-16). It
exists as its OWN node - not as a key inside the Associations dict - so that a
scientist reading the canvas can see that a probabilistic law is in force
without opening any dictionary (Readability Contract R1.6).

The protocol, for each gene input listed here:

    probability = hill_max - hill_max / (1 + (conc / threshold)^hill_exponent)
    input ON    = probability > cell_random

- `threshold` is the input's association threshold - owned by the Associations
  dict on the Setup Associations node (single source of truth, R2.2). It is
  deliberately NOT repeated here.
- `cell_random` is a persistent per-cell value in [0, 1), drawn at cell
  creation and re-drawn for daughters at division. It gives stable
  cell-to-cell variability in drug response.
- Inputs NOT listed here keep the deterministic test: conc > threshold.

This node only WRITES the configuration (`input_activations`). It is consumed
every step by `apply_associations_to_inputs` (the law's single implementation:
`hill_probability` in that module) and at t=0 by
`initialize_netlogo_gene_networks`, which resolves the same store.

In the NetLogo reference the probabilistic inputs are MCT1I (uses the cell's
ran1) and GLUT1I (ran2), with hill_max 0.85 and hill_exponent 1.0.
"""

from typing import Dict, Any, Union
from src.workflow.decorators import register_function


def _to_float(value):
    """Coerce a GUI value ("0.85", 0.85, "") to float or None."""
    if value is None or value == '':
        return None
    return float(value)


@register_function(
    typed_env_exempt=True,
    display_name="Hill (Probabilistic) Input Activation",
    description="Mark gene inputs as probabilistic (NetLogo hill law): "
                "p = hill_max - hill_max/(1 + (conc/threshold)^hill_exponent), "
                "ON if p > the cell's persistent random. Threshold = the input's "
                "association threshold. Unlisted inputs stay deterministic.",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "hill_activations",
            "type": "DICT",
            "description": "Dict mapping gene input names (e.g. MCT1I, GLUT1I) to "
                           "{hill_max, hill_exponent}. Listing an input makes it "
                           "probabilistic; omit hill_max/hill_exponent to use the "
                           "NetLogo defaults (0.85, 1.0).",
            "default": {}
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def set_hill_input_activation(
    context: Dict[str, Any],
    hill_activations: Union[Dict, None] = None,
    **kwargs
) -> bool:
    """
    Store which gene inputs use the probabilistic hill activation law.

    Writes `input_activations`: {gene_input: {hill_max, hill_exponent}} to the
    config (full simulation mode) or the context (simple mode). Presence of an
    input in the store is what switches it from the deterministic
    conc > threshold test to the hill law - see the module docstring for the
    full protocol.
    """
    try:
        parsed = {}
        if isinstance(hill_activations, dict):
            for gene_input, entry in hill_activations.items():
                entry = entry if isinstance(entry, dict) else {}
                parsed[gene_input] = {
                    'hill_max': _to_float(entry.get('hill_max')),
                    'hill_exponent': _to_float(entry.get('hill_exponent')),
                }
        # dictParameterNode may expand entries as individual kwargs
        elif kwargs:
            for gene_input, entry in kwargs.items():
                if isinstance(entry, dict):
                    parsed[gene_input] = {
                        'hill_max': _to_float(entry.get('hill_max')),
                        'hill_exponent': _to_float(entry.get('hill_exponent')),
                    }

        config = context.get('config')
        if config is not None:
            config.input_activations = parsed
        else:
            context['input_activations'] = parsed

        for gene_input, entry in parsed.items():
            hm = entry['hill_max'] if entry['hill_max'] is not None else 0.85
            he = entry['hill_exponent'] if entry['hill_exponent'] is not None else 1.0
            print(f"[HILL ACTIVATION] {gene_input}: probabilistic "
                  f"(hill_max={hm:g}, hill_exponent={he:g}, "
                  f"threshold from its association)")
        if not parsed:
            print("[HILL ACTIVATION] No inputs listed - all inputs deterministic")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to set hill input activation: {e}")
        import traceback
        traceback.print_exc()
        return False
