"""
Initialization workflow functions (kernel / spatial / IO only).

These set up the substrate/domain/IO infrastructure without requiring YAML
config files. Biology setup (population, gene networks, associations, MaBoSS,
cell loading/generation) has moved to opencellcomms_adapters/common/.
"""

from .setup_simulation import setup_simulation
from .setup_domain import setup_domain
from .setup_substances import setup_substances
from .add_substance import add_substance
from .finalize_substances import finalize_substances
from .setup_output import setup_output
from .setup_environment import setup_environment
from .setup_scene import setup_scene
from .setup_space import setup_space
from .setup_resource import setup_resource
from .setup_custom_parameters import setup_custom_parameters
from .read_checkpoint import read_checkpoint

__all__ = [
    'setup_simulation',
    'setup_domain',
    'setup_substances',
    'add_substance',
    'finalize_substances',
    'setup_output',
    'setup_environment',
    'setup_scene',
    'setup_space',
    'setup_resource',
    'setup_custom_parameters',
    'read_checkpoint',
]

