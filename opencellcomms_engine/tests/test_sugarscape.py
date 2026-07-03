"""Sugarscape adapter: behaviour ordering (fast) and a full executor run (slow).

The adapter had no tests; the shipped workflow was never executed by CI. These
cover the reference model end-to-end on the real executor path.
"""

from pathlib import Path

import numpy as np
import pytest

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import FieldResource
from src.abm.world import LatticeWorld
from src.biology.context import BiologicalContext

from opencellcomms_adapters.SUGARSCAPE.functions.forager.move_to_best_sugar import move_to_best_sugar
from opencellcomms_adapters.SUGARSCAPE.functions.forager.eat_sugar import eat_sugar
from opencellcomms_adapters.SUGARSCAPE.functions.forager.metabolize import metabolize
from opencellcomms_adapters.SUGARSCAPE.functions.forager.cull_starved import cull_starved
from src.workflow.functions.reconciliation.apply_reconciliation import apply_reconciliation

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / "opencellcomms_adapters" / "SUGARSCAPE" / "workflows" / "sugarscape.json"
)


def _forager_ctx():
    world = LatticeWorld(6, 1, 1.0, "bounded", "bounded")
    pop = Population(world, context={}, seed=1)
    dom = Domain(world)
    dom.add_resource(FieldResource("sugar", world, initial=0.0))
    pop.domain = dom
    return {"domain": dom, "abm_population": pop, "_rng": np.random.default_rng(1)}, dom, pop


def _forager_step(ctx, pop, agents):
    """One scheduler step: ask each forager, then world_step (reconcile + cull)."""
    for a in agents:
        ctx["_current_agent"] = a
        ctx["_current_cell"] = a.cell
        env = BiologicalContext(ctx)
        move_to_best_sugar(env)
        eat_sugar(env)
        metabolize(env)
    ctx["_current_agent"] = ctx["_current_cell"] = None
    env = BiologicalContext(ctx)
    apply_reconciliation(env)
    cull_starved(env)


def test_forager_eats_before_starving():
    """A forager on a rich tile must not be culled on its pre-eat balance: eating
    is credited in reconciliation before cull_starved makes the death call."""
    ctx, dom, pop = _forager_ctx()
    dom.resource("sugar").set_at((2, 0), 100.0)
    a = pop.spawn((2, 0), kind="forager", sugar=1.0, metabolism=5.0, vision=1)

    _forager_step(ctx, pop, [a])

    survivor = pop.agent_by_id(a.id)
    assert survivor is not None                      # survived (1 - 5 + 100 = 96)
    assert survivor.get("sugar") == pytest.approx(96.0)


def test_truly_starved_forager_is_culled():
    ctx, dom, pop = _forager_ctx()
    # No sugar anywhere; a low-reserve, high-burn forager should die this step.
    a = pop.spawn((2, 0), kind="forager", sugar=1.0, metabolism=5.0, vision=1)

    _forager_step(ctx, pop, [a])

    assert pop.agent_by_id(a.id) is None


def _load_workflow(steps):
    from src.workflow.loader import WorkflowLoader
    import opencellcomms_adapters.SUGARSCAPE.register  # noqa: F401 (register plugin funcs)

    wf = WorkflowLoader.load(WORKFLOW)
    for call in wf.subworkflows["main"].subworkflow_calls:
        if call.subworkflow_name == "__scheduler__":
            call.iterations = steps
    # Plot nodes are irrelevant to the mechanics under test and add file IO.
    for sub in wf.subworkflows.values():
        for fn in sub.functions:
            if fn.function_name.startswith("plot_"):
                fn.enabled = False
    return wf


def _run(steps):
    from src.workflow.executor import WorkflowExecutor

    ex = WorkflowExecutor(_load_workflow(steps), observability_enabled=False)
    ctx = ex.execute_main({})
    pop = ctx["abm_population"]
    positions = sorted(c.state.position for c in pop.cellpop.state.cells.values())
    return pop, positions


@pytest.mark.slow
def test_sugarscape_runs_through_executor():
    pop, positions = _run(steps=10)
    # Invariants of the real run:
    assert pop.count() > 0                                    # population does not collapse
    assert pop.count() < 120                                  # some foragers starved
    assert len(positions) == len(set(positions))             # one agent per tile
    assert len(pop.cellpop.state.spatial_grid) == pop.count()  # occupancy index consistent


@pytest.mark.slow
def test_sugarscape_is_deterministic():
    _, first = _run(steps=10)
    _, second = _run(steps=10)
    assert first == second                                   # same seed -> identical state
