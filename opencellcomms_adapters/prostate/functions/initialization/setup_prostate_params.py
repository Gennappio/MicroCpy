"""Load prostate-specific ``user_parameters`` from a PhysiCell XML config.

Reads the prostate user_parameters block (apoptosis_rate_multiplier,
base_transition_rate, transition_rate_multiplier, migration_speed / bias /
persistence, and per-drug ``<drug>_maxc / _xmid / _scal``) and stores them
on the shared context for the prostate workflow functions.

Also derives:
  * ``prostate_drug_params``  - {drug_name: {max_conc, xmid, scale, uptake_rate}}
  * ``prostate_drug_substances`` - list of drug names (substrates minus oxygen)
  * ``prostate_params``       - flat dict of phenotype coupling scalars
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log
from opencellcomms_adapters.prostate.drug_sensitivity import DRUG_TARGETS


@register_function(
    display_name="Prostate: Load user_parameters from XML",
    description=(
        "Parse the PhysiCell XML <user_parameters> block for the prostate "
        "project and populate context['prostate_params'] / "
        "context['prostate_drug_params']."
    ),
    category="INITIALIZATION",
    parameters=[
        {"name": "xml_path", "type": "STRING",
         "description": "Path to PhysiCell_settings_LNCaP*.xml",
         "default": ""},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def setup_prostate_params(
    context: Dict[str, Any],
    xml_path: str = "",
    **kwargs,
) -> None:
    if not xml_path:
        xml_path = context.get("prostate_xml_path", "")
    if not xml_path:
        return

    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    up = root.find(".//user_parameters")
    if up is None:
        return

    # Flat scalars
    flat: Dict[str, float] = {}
    simulation_mode = -1
    cell_line = "LNCaP"
    for el in up:
        tag = el.tag
        txt = (el.text or "").strip()
        if not txt:
            continue
        if tag == "simulation_mode":
            try:
                simulation_mode = int(txt)
            except ValueError:
                pass
            continue
        if tag == "cell_line":
            cell_line = txt
            continue
        try:
            flat[tag] = float(txt)
        except ValueError:
            pass

    prostate_params: Dict[str, float] = {
        "base_apoptosis_rate": flat.get("base_apoptosis_rate", 5.31667e-05),
        "apoptosis_rate_multiplier": flat.get("apoptosis_rate_multiplier", 5.0),
        "base_transition_rate": flat.get("base_transition_rate", 0.0003155),
        "transition_rate_multiplier": flat.get("transition_rate_multiplier", 2.0),
        "migration_speed": flat.get("migration_speed", 0.35),
        "migration_bias": flat.get("migration_bias", 0.0),
        "persistence": flat.get("persistence", 2.0),
    }

    # Extract per-drug (xmid, scale, max_conc, uptake).
    drug_params: Dict[str, Dict[str, float]] = {}
    for drug in DRUG_TARGETS.keys():
        maxc = flat.get(f"{drug}_maxc")
        xmid = flat.get(f"{drug}_xmid")
        scal = flat.get(f"{drug}_scal")
        if maxc is None or xmid is None or scal is None:
            continue
        drug_params[drug] = {
            "max_conc": maxc,
            "xmid": xmid,
            "scale": scal,
            "uptake_rate": flat.get(f"{drug}_uptake_rate", 0.0),
            "secretion_rate": flat.get(f"{drug}_secretion_rate", 0.0),
        }

    # Drug-bath concentration (from <drug_concentration_<drug>> - string "0",
    # "IC50", "IC90" etc.). We store raw strings; consumer decides.
    drug_bath_raw: Dict[str, str] = {}
    for el in up:
        if el.tag.startswith("drug_concentration_"):
            drug = el.tag[len("drug_concentration_"):]
            drug_bath_raw[drug] = (el.text or "").strip()

    context["prostate_params"] = prostate_params
    context["prostate_drug_params"] = drug_params
    context["prostate_drug_bath_labels"] = drug_bath_raw
    context["prostate_simulation_mode"] = simulation_mode
    context["prostate_cell_line"] = cell_line
    context["prostate_xml_path"] = str(Path(xml_path).resolve())

    log(context, f"Prostate: loaded {len(drug_params)} drugs "
                 f"({', '.join(drug_params.keys()) or 'none'}); "
                 f"simulation_mode={simulation_mode} cell_line={cell_line}",
        prefix="[Prostate]")
