"""
Sugarscape behaviours — atomic nodes (one file = one node = one .py function).

These are the nodes you wire on the entity canvases:

  Resource (sugar / max_sugar):
    Setup: seed_max_sugar, seed_sugar      Step: grow_sugar
  Agent (forager):
    Setup: place_foragers (collective, once)
    Step (per-agent, run via the "ask"): move_to_best_sugar -> eat_sugar -> metabolize
  Population:
    Step: cull_starved

Agent-step nodes operate on `env.agent` (the single agent the per-agent loop is
currently asking). Resource/collective nodes operate on the whole field/population.
All read the world through the typed `env` API.
"""

import numpy as np

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


# ── Resource behaviours (whole field, run once) ──────────────────────────────

@register_function(
    display_name="Seed Max Sugar", description="Fill 'max_sugar' with two sugar mountains",
    category="INITIALIZATION", inputs=["context"], outputs=[], compatible_kernels=["*"],
    requires=[], operates_on=["max_sugar"],
    parameters=[
        {"name": "peak", "type": "FLOAT", "default": 4.0},
        {"name": "radius_frac", "type": "FLOAT", "default": 0.45},
    ],
)
def seed_max_sugar(env: BiologicalContext, peak: float = 4.0, radius_frac: float = 0.45, **kwargs):
    sp = env.space
    vals = env.resource("max_sugar").values()
    nx, ny = sp.nx, sp.ny
    centers = [(0.3 * nx, 0.7 * ny), (0.7 * nx, 0.3 * ny)]
    radius = max(1.0, radius_frac * nx)
    for tj in range(ny):
        for ti in range(nx):
            cap = 0.0
            for cx, cy in centers:
                d = ((ti - cx) ** 2 + (tj - cy) ** 2) ** 0.5
                cap = max(cap, peak * max(0.0, 1.0 - d / radius))
            vals[tj, ti] = float(round(cap))


@register_function(
    display_name="Seed Sugar (full)", description="Start 'sugar' at full capacity (= max_sugar)",
    category="INITIALIZATION", inputs=["context"], outputs=[], compatible_kernels=["*"],
    requires=[], operates_on=["sugar"],
)
def seed_sugar(env: BiologicalContext, **kwargs):
    env.resource("sugar").values()[:] = env.resource("max_sugar").values()


@register_function(
    display_name="Grow Sugar", description="Regrow 'sugar' toward 'max_sugar' by a fixed rate",
    category="ENVIRONMENT", inputs=["context"], outputs=[], compatible_kernels=["*"],
    requires=[], operates_on=["sugar"],
    parameters=[{"name": "rate", "type": "FLOAT", "default": 1.0}],
)
def grow_sugar(env: BiologicalContext, rate: float = 1.0, **kwargs):
    env.resource("sugar").grow_to(env.resource("max_sugar").values(), float(rate))


# ── Agent placement (collective Setup, run once) ─────────────────────────────

@register_function(
    display_name="Place Foragers", description="Scatter a kind's agents on empty tiles with traits",
    category="INITIALIZATION", inputs=["context"], outputs=[], compatible_kernels=["*"], requires=[],
    parameters=[
        {"name": "kind", "type": "STRING", "default": "forager"},
        {"name": "count", "type": "INT", "default": 300},
        {"name": "sugar_min", "type": "FLOAT", "default": 5.0},
        {"name": "sugar_max", "type": "FLOAT", "default": 25.0},
        {"name": "metabolism_min", "type": "FLOAT", "default": 1.0},
        {"name": "metabolism_max", "type": "FLOAT", "default": 4.0},
        {"name": "vision_min", "type": "INT", "default": 1},
        {"name": "vision_max", "type": "INT", "default": 6},
    ],
)
def place_foragers(env: BiologicalContext, kind: str = "forager", count: int = 300,
                   sugar_min: float = 5.0, sugar_max: float = 25.0,
                   metabolism_min: float = 1.0, metabolism_max: float = 4.0,
                   vision_min: int = 1, vision_max: int = 6, **kwargs):
    env.population.populate(
        kind, int(count),
        sugar=lambda rng: float(rng.uniform(sugar_min, sugar_max)),
        metabolism=lambda rng: float(rng.uniform(metabolism_min, metabolism_max)),
        vision=lambda rng: int(rng.integers(vision_min, vision_max + 1)),
    )


# ── Agent Step — atomic, per-agent (env.agent) ───────────────────────────────

@register_function(
    display_name="Move to Best Sugar", description="Agent moves to the most sugar within its vision",
    category="INTERCELLULAR", inputs=["context"], outputs=[], compatible_kernels=["*"],
    requires=[], operates_on=["sugar"],
)
def move_to_best_sugar(env: BiologicalContext, **kwargs):
    a = env.agent
    if a is None:
        return
    sp, sugar = env.space, env.resource("sugar")
    pos = a.position
    vision = int(a.get("vision", 1))
    best, best_s, best_d = pos, sugar.at(pos), 0.0
    for cell in sp.neighbors(pos, vision, "axial"):
        if not sp.is_free(cell):
            continue
        s, d = sugar.at(cell), sp.distance(pos, cell)
        if s > best_s or (s == best_s and d < best_d):
            best, best_s, best_d = cell, s, d
    if best != pos:
        a.move_to(best)


@register_function(
    display_name="Eat Sugar", description="Agent eats all sugar on its tile",
    category="INTERCELLULAR", inputs=["context"], outputs=[], compatible_kernels=["*"],
    requires=[], operates_on=["sugar"],
)
def eat_sugar(env: BiologicalContext, **kwargs):
    a = env.agent
    if a is None:
        return
    r = env.resource("sugar")
    got = r.at(a.position)
    r.set_at(a.position, 0.0)
    a.set("sugar", a.get("sugar", 0.0) + got)


@register_function(
    display_name="Metabolize", description="Agent burns sugar; dies (requests removal) if it runs out",
    category="INTERCELLULAR", inputs=["context"], outputs=[], compatible_kernels=["*"], requires=[],
)
def metabolize(env: BiologicalContext, **kwargs):
    a = env.agent
    if a is None:
        return
    a.set("sugar", a.get("sugar", 0.0) - a.get("metabolism", 1.0))
    if a.get("sugar", 0.0) < 0:
        a.die()


# ── Population Step (collective, run once) ───────────────────────────────────

@register_function(
    display_name="Cull Starved Agents", description="Remove agents that ran out of sugar this step",
    category="INTERCELLULAR", inputs=["context"], outputs=[], compatible_kernels=["*"], requires=[],
)
def cull_starved(env: BiologicalContext, **kwargs):
    env.population.cull()


@register_function(
    display_name="Census", description="Print a one-line census (agents + resource totals)",
    category="FINALIZATION", inputs=["context"], outputs=[], compatible_kernels=["*"], requires=[],
)
def census(env: BiologicalContext, **kwargs):
    pop, dom = env.population, env.domain
    parts = [f"agents={pop.count()}"] + [f"{r.name}={r.total():.0f}" for r in dom.resources()]
    print("[census] " + "  ".join(parts))
