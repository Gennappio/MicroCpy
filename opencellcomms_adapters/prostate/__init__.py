"""Prostate experiment adapter — LNCaP drug-response model (PhysiBoSS replica).

Replicates the PhysiBoSS `prostate` sample project
(`sample_projects_intracellular/boolean/prostate`) in the OpenCellComms
workflow engine.

The native project wires three C++ custom modules:
    custom.cpp                  -> cell-type setup and tumor-cell phenotype
    boolean_model_interface.cpp -> pre/post-update intracellular coupling
    drug_sensitivity.cpp        -> GDSC-style logistic dose-response curves

Those modules are ported here as Python workflow functions so the logic is
visible in the GUI and composable with the rest of the engine.
"""
