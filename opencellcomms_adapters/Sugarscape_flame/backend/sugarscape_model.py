"""
Sugarscape as a FLAME GPU 2 model.

This is the GPU port of the CPU Sugarscape (opencellcomms_adapters/SUGARSCAPE):
50x50 toroidal grid, a two-peak sugar capacity landscape with growback, and
foragers that each step move toward the best sugar within their vision, eat it,
and metabolize (dying when depleted). The port maps the CPU semantics onto FLAME
GPU's data-parallel, message-passing model:

    CPU (Python, one agent at a time)      FLAME GPU (all agents in parallel)
    -----------------------------------    ------------------------------------
    agent.neighbors()/sense()          ->  read a MessageArray2D over the grid
    request_move + reconciliation      ->  bid to a MessageBucket keyed by the
      (one agent per tile)                 target cell; the cell arbitrates one
                                           winner (deferred-commit == GPU layers)
    resource field (sugar)             ->  a `cell` agent per tile
    Population.cull (starved)          ->  agent function returns flamegpu::DEAD

Per-step layer pipeline (each layer runs all its agents concurrently):
  1. forager_occupy   forager writes its id+1 into occupancy[x,y]
  2. cell_grow        cell grows sugar, reads occupancy, emits cell_sugar[x,y]
  3. forager_choose   forager scans cell_sugar over its (axial) vision, picks the
                      best FREE tile, bids {id,wealth} to the target cell's bucket
  4. cell_arbitrate   cell picks the richest bidder, emits grant[x,y]={winner,sugar},
                      and zeroes its own sugar if it granted (eaten)
  5. forager_apply    winner moves + eats granted sugar; everyone metabolizes;
                      depleted foragers return DEAD

NOTE — this model is structurally complete but has NOT been compiled/run here
(no pyflamegpu wheel for this interpreter). The RTC CUDA below follows FLAME GPU
2 conventions; treat the first on-GPU run as the acceptance test and expect to
fine-tune message-API details. Simplification vs. the CPU model: a forager that
loses an arbitration stays put and does not eat that step (the CPU version's
tie-break/ordering differ), so trajectories match in aggregate, not per-agent.
"""
from typing import Dict, List

import numpy as np


# --------------------------------------------------------------------------- #
# RTC agent-function sources (CUDA C++, compiled by FLAME GPU at model build).
# --------------------------------------------------------------------------- #

_FORAGER_OCCUPY = r"""
FLAMEGPU_AGENT_FUNCTION(forager_occupy, flamegpu::MessageNone, flamegpu::MessageArray2D) {
    const int x = FLAMEGPU->getVariable<int>("x");
    const int y = FLAMEGPU->getVariable<int>("y");
    // Store id+1 so an unwritten (default 0) index reads as "free".
    FLAMEGPU->message_out.setVariable<int>("occupant", FLAMEGPU->getVariable<int>("id") + 1);
    FLAMEGPU->message_out.setIndex(x, y);
    return flamegpu::ALIVE;
}
"""

_CELL_GROW = r"""
FLAMEGPU_AGENT_FUNCTION(cell_grow, flamegpu::MessageArray2D, flamegpu::MessageArray2D) {
    const int x = FLAMEGPU->getVariable<int>("x");
    const int y = FLAMEGPU->getVariable<int>("y");
    const float rate = FLAMEGPU->environment.getProperty<float>("growback");
    float sugar = FLAMEGPU->getVariable<float>("sugar");
    const float cap = FLAMEGPU->getVariable<float>("max_sugar");
    sugar = fminf(cap, sugar + rate);
    FLAMEGPU->setVariable<float>("sugar", sugar);

    const int occupant = FLAMEGPU->message_in.at(x, y).getVariable<int>("occupant"); // 0 == free
    FLAMEGPU->message_out.setVariable<float>("sugar", sugar);
    FLAMEGPU->message_out.setVariable<int>("occupant", occupant);
    FLAMEGPU->message_out.setIndex(x, y);
    return flamegpu::ALIVE;
}
"""

# Axial (4-ray) vision, toroidal wrap — mirrors world.neighbors(pattern="axial").
_FORAGER_CHOOSE = r"""
FLAMEGPU_AGENT_FUNCTION(forager_choose, flamegpu::MessageArray2D, flamegpu::MessageBucket) {
    const int G = (int)FLAMEGPU->environment.getProperty<unsigned int>("GRID");
    const int x = FLAMEGPU->getVariable<int>("x");
    const int y = FLAMEGPU->getVariable<int>("y");
    const int vision = FLAMEGPU->getVariable<int>("vision");
    const int myid = FLAMEGPU->getVariable<int>("id");

    // Start with the current tile (agents may stay and eat).
    int best_x = x, best_y = y;
    float best_sugar = FLAMEGPU->message_in.at(x, y).getVariable<float>("sugar");
    int best_dist = 0;

    const int dirs[4][2] = { {1,0}, {-1,0}, {0,1}, {0,-1} };
    for (int d = 0; d < 4; ++d) {
        for (int r = 1; r <= vision; ++r) {
            int nx = ((x + dirs[d][0]*r) % G + G) % G;
            int ny = ((y + dirs[d][1]*r) % G + G) % G;
            auto m = FLAMEGPU->message_in.at(nx, ny);
            const int occ = m.getVariable<int>("occupant");     // 0 free, else id+1
            if (occ != 0 && occ != myid + 1) continue;          // occupied by someone else
            const float s = m.getVariable<float>("sugar");
            if (s > best_sugar || (s == best_sugar && r < best_dist)) {
                best_sugar = s; best_x = nx; best_y = ny; best_dist = r;
            }
        }
    }

    FLAMEGPU->setVariable<int>("target_x", best_x);
    FLAMEGPU->setVariable<int>("target_y", best_y);

    // Bid for the chosen tile; the cell arbitrates a single winner.
    FLAMEGPU->message_out.setKey((unsigned int)(best_y * G + best_x));
    FLAMEGPU->message_out.setVariable<int>("id", myid);
    FLAMEGPU->message_out.setVariable<float>("wealth", FLAMEGPU->getVariable<float>("sugar"));
    return flamegpu::ALIVE;
}
"""

_CELL_ARBITRATE = r"""
FLAMEGPU_AGENT_FUNCTION(cell_arbitrate, flamegpu::MessageBucket, flamegpu::MessageArray2D) {
    const int G = (int)FLAMEGPU->environment.getProperty<unsigned int>("GRID");
    const int x = FLAMEGPU->getVariable<int>("x");
    const int y = FLAMEGPU->getVariable<int>("y");
    const unsigned int key = (unsigned int)(y * G + x);

    int winner = -1;
    float best_wealth = -1.0f;
    for (const auto& m : FLAMEGPU->message_in(key)) {
        const float w = m.getVariable<float>("wealth");
        const int id = m.getVariable<int>("id");
        if (w > best_wealth || (w == best_wealth && (winner < 0 || id < winner))) {
            best_wealth = w; winner = id;
        }
    }

    const float sugar = FLAMEGPU->getVariable<float>("sugar");
    FLAMEGPU->message_out.setVariable<int>("winner", winner + 1);       // 0 == no winner
    FLAMEGPU->message_out.setVariable<float>("sugar_available", winner >= 0 ? sugar : 0.0f);
    FLAMEGPU->message_out.setIndex(x, y);
    if (winner >= 0) FLAMEGPU->setVariable<float>("sugar", 0.0f);       // eaten
    return flamegpu::ALIVE;
}
"""

_FORAGER_APPLY = r"""
FLAMEGPU_AGENT_FUNCTION(forager_apply, flamegpu::MessageArray2D, flamegpu::MessageNone) {
    const int tx = FLAMEGPU->getVariable<int>("target_x");
    const int ty = FLAMEGPU->getVariable<int>("target_y");
    const int myid = FLAMEGPU->getVariable<int>("id");

    auto grant = FLAMEGPU->message_in.at(tx, ty);
    float sugar = FLAMEGPU->getVariable<float>("sugar");
    if (grant.getVariable<int>("winner") == myid + 1) {
        FLAMEGPU->setVariable<int>("x", tx);
        FLAMEGPU->setVariable<int>("y", ty);
        sugar += grant.getVariable<float>("sugar_available");
    }
    sugar -= FLAMEGPU->getVariable<float>("metabolism");
    FLAMEGPU->setVariable<float>("sugar", sugar);
    return sugar < 0.0f ? flamegpu::DEAD : flamegpu::ALIVE;
}
"""


def _capacity_landscape(grid: int, peak: float, radius_frac: float) -> np.ndarray:
    """Two-peak carrying capacity, matching seed_sugar_capacity.py."""
    cap = np.zeros((grid, grid), dtype=np.float32)
    centers = [(0.3 * grid, 0.7 * grid), (0.7 * grid, 0.3 * grid)]
    radius = max(1.0, radius_frac * grid)
    for ty in range(grid):
        for tx in range(grid):
            c = 0.0
            for cx, cy in centers:
                d = ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5
                c = max(c, peak * max(0.0, 1.0 - d / radius))
            cap[ty, tx] = float(round(c))
    return cap


def build_model(params: Dict):
    """Construct the pyflamegpu ModelDescription (agents, messages, layers)."""
    import pyflamegpu

    grid = int(params["grid_size"])
    model = pyflamegpu.ModelDescription("sugarscape")

    env = model.Environment()
    env.newPropertyUInt("GRID", grid)
    env.newPropertyFloat("growback", float(params["growback_rate"]))

    # Messages -------------------------------------------------------------
    occ = model.newMessageArray2D("occupancy")
    occ.setDimensions(grid, grid)
    occ.newVariableInt("occupant")

    cell_sugar = model.newMessageArray2D("cell_sugar")
    cell_sugar.setDimensions(grid, grid)
    cell_sugar.newVariableFloat("sugar")
    cell_sugar.newVariableInt("occupant")

    bids = model.newMessageBucket("bids")
    bids.setBounds(0, grid * grid)
    bids.newVariableInt("id")
    bids.newVariableFloat("wealth")

    grant = model.newMessageArray2D("grant")
    grant.setDimensions(grid, grid)
    grant.newVariableInt("winner")
    grant.newVariableFloat("sugar_available")

    # Agents ---------------------------------------------------------------
    cell = model.newAgent("cell")
    cell.newVariableInt("x")
    cell.newVariableInt("y")
    cell.newVariableFloat("sugar")
    cell.newVariableFloat("max_sugar")
    f_grow = cell.newRTCFunction("cell_grow", _CELL_GROW)
    f_grow.setMessageInput("occupancy")
    f_grow.setMessageOutput("cell_sugar")
    f_arb = cell.newRTCFunction("cell_arbitrate", _CELL_ARBITRATE)
    f_arb.setMessageInput("bids")
    f_arb.setMessageOutput("grant")

    forager = model.newAgent("forager")
    for v in ("id", "x", "y", "vision", "target_x", "target_y"):
        forager.newVariableInt(v)
    forager.newVariableFloat("sugar")
    forager.newVariableFloat("metabolism")
    f_occ = forager.newRTCFunction("forager_occupy", _FORAGER_OCCUPY)
    f_occ.setMessageOutput("occupancy")
    f_choose = forager.newRTCFunction("forager_choose", _FORAGER_CHOOSE)
    f_choose.setMessageInput("cell_sugar")
    f_choose.setMessageOutput("bids")
    f_apply = forager.newRTCFunction("forager_apply", _FORAGER_APPLY)
    f_apply.setMessageInput("grant")
    f_apply.setAllowAgentDeath(True)

    # Layers (execution order) --------------------------------------------
    for agent_name, fn in (
        ("forager", "forager_occupy"),
        ("cell", "cell_grow"),
        ("forager", "forager_choose"),
        ("cell", "cell_arbitrate"),
        ("forager", "forager_apply"),
    ):
        layer = model.newLayer()
        layer.addAgentFunction(agent_name, fn)

    return model


def _seed_populations(model, params, rng):
    import pyflamegpu

    grid = int(params["grid_size"])
    cap = _capacity_landscape(grid, float(params["sugar_peak"]), float(params["radius_frac"]))

    cells = pyflamegpu.AgentVector(model.Agent("cell"), grid * grid)
    i = 0
    for y in range(grid):
        for x in range(grid):
            a = cells[i]; i += 1
            a.setVariableInt("x", x)
            a.setVariableInt("y", y)
            a.setVariableFloat("max_sugar", float(cap[y, x]))
            a.setVariableFloat("sugar", float(cap[y, x]))

    n = int(params["n_foragers"])
    coords = rng.permutation(grid * grid)[:n]
    foragers = pyflamegpu.AgentVector(model.Agent("forager"), n)
    for k, lin in enumerate(coords):
        a = foragers[k]
        a.setVariableInt("id", int(k))
        a.setVariableInt("x", int(lin % grid))
        a.setVariableInt("y", int(lin // grid))
        a.setVariableInt("vision", int(rng.integers(params["vision_min"], params["vision_max"] + 1)))
        a.setVariableInt("target_x", int(lin % grid))
        a.setVariableInt("target_y", int(lin // grid))
        a.setVariableFloat("sugar", float(rng.uniform(params["sugar_min"], params["sugar_max"])))
        a.setVariableFloat("metabolism", float(rng.uniform(params["metabolism_min"], params["metabolism_max"])))
    return cells, foragers


def run_model(params: Dict) -> Dict[str, List[float]]:
    """Build, seed, and step the model; return per-step population + total sugar."""
    import pyflamegpu

    history = {"population": [], "total_sugar": []}

    class Recorder(pyflamegpu.HostFunction):
        def run(self, FLAMEGPU):
            history["population"].append(int(FLAMEGPU.agent("forager").count()))
            history["total_sugar"].append(float(FLAMEGPU.agent("cell").sumFloat("sugar")))

    model = build_model(params)
    model.addStepFunction(Recorder())

    rng = np.random.default_rng(int(params["seed"]) or None)
    cells, foragers = _seed_populations(model, params, rng)

    sim = pyflamegpu.CUDASimulation(model)
    sim.SimulationConfig().steps = int(params["steps"])
    sim.SimulationConfig().random_seed = int(params["seed"])
    sim.setPopulationData(cells)
    sim.setPopulationData(foragers)
    sim.simulate()
    return history
