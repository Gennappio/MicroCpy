"""
PhysiBoss adapter for OpenCellComms.

Wraps PhysiCell/PhysiBoss simulation models so that existing PhysiCell XML
configs (with MaBoSS Boolean network coupling) can be loaded, visualised,
modified, and executed as OpenCellComms workflows.

Modules:
    config_loader    - Parse PhysiCell XML → Python dataclasses
    coupling         - Substance ↔ BN node threshold mapping
    phenotype_mapper - BN output nodes → cell fate rates
    cycle_model      - Stochastic cell-cycle phase transitions
"""

from .config_loader import PhysiBossConfigLoader, PhysiBossConfig
from .coupling import PhysiBossSubstrateCoupling
from .phenotype_mapper import PhysiBossPhenotypeMapper
from .cycle_model import CycleModel

__all__ = [
    "PhysiBossConfigLoader",
    "PhysiBossConfig",
    "PhysiBossSubstrateCoupling",
    "PhysiBossPhenotypeMapper",
    "CycleModel",
]
