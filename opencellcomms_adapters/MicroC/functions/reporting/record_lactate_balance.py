"""Capture viable-cell lactate exchange after the metabolic diffusion solve.

For the cells viable at this phase (neither Necrosis nor Apoptosis):
    production = sum(cell.metabolic_state['lactate_production'])
    consumption = sum(cell.metabolic_state['lactate_consumption'])
    balance = production - consumption

All three are total rates in mol/s. Positive balance means net release;
negative means net uptake. The metabolism node owns the per-cell rates,
including its conversion factors and fate weights; this node never recomputes
or rescales them. Gross totals retain simultaneous production and consumption.
This measures cellular exchange, not boundary flux, concentration accumulation,
or evidence that consumed lactate originated from other tumour cells.

Place after diffusion and before gene/fate updates. The sensitivity reporter
reads this snapshot for the same scheduler iteration, even if cells subsequently
change fate. A missing/non-converged solve or incomplete/non-finite rates leaves
the snapshot undefined. An empty viable population has zero total exchange.
raw_context is used only for the scheduler counter and solver diagnostics,
which have no typed accessor.
"""

import math

from src.biology.context import BiologicalContext, Phenotype
from src.workflow.decorators import register_function


@register_function(
    requires=['population'],
    display_name='Record Lactate Balance',
    description=(
        'Snapshot viable-cell lactate production and consumption after diffusion, '
        'before gene/fate updates. Balance = total production - total consumption '
        '(mol/s): positive means release, negative means uptake. Uses the metabolism '
        "node's stored rates and weights; excludes Necrosis and Apoptosis. Missing "
        'rates or a non-converged solve leave the values undefined.'
    ),
    category='FINALIZATION',
    parameters=[],
    inputs=['context'],
    outputs=[],
    cloneable=False,
    collective=True,
    compatible_kernels=['biophysics'],
    contract={
        'phase': 'reporting',
        'owner': {'type': 'agent', 'kind': 'tumor_cell'},
        'reads': ['agent.collection', 'agent.self.metabolic_state'],
        'writes': [],
        'emits': [],
    },
)
def record_lactate_balance(env: BiologicalContext, **kwargs) -> bool:
    iteration = env.raw_context.get('loop_iteration')
    solve = env.raw_context.get('numerical_diagnostics', {}).get('last_coupling', {})
    snapshot = {'iteration': iteration, 'status': 'no converged metabolic solve'}
    if (iteration is not None and solve.get('iteration') == iteration
            and solve.get('converged') is True):
        production, consumption = [], []
        for cell in env.cells:
            if cell.phenotype in (Phenotype.NECROSIS.value, Phenotype.APOPTOSIS.value):
                continue
            rates = cell.metabolic_state
            try:
                p = float(rates['lactate_production'])
                u = float(rates['lactate_consumption'])
            except (KeyError, TypeError, ValueError):
                snapshot['status'] = 'missing lactate rates'
                break
            if not (math.isfinite(p) and math.isfinite(u) and p >= 0 and u >= 0):
                snapshot['status'] = 'invalid lactate rates'
                break
            production.append(p)
            consumption.append(u)
        else:
            p, u = math.fsum(production), math.fsum(consumption)
            snapshot.update(status='ok', lactate_production_mol_s=p,
                            lactate_consumption_mol_s=u, lactate_balance_mol_s=p - u)

    env.results.store('lactate_balance', snapshot)
    if snapshot['status'] != 'ok':
        print(f"[LACTATE] Iteration {iteration}: {snapshot['status']}; exchange values left blank")
    return True
