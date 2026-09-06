"""Run-owned random state, including the legacy generators used by adapters.

Planner replicates run in isolated processes. Seeding the legacy globals here
keeps older functions reproducible while typed functions use env.rng.
"""
import random
import secrets

import numpy as np

RNG_SCHEME = "occ-seed-v1"


def seed_run(context, seed=None):
    effective = 42 if seed is None else int(seed)
    if effective < 0:
        raise ValueError("Run seed must be non-negative")
    if effective == 0:
        effective = secrets.randbits(128) or 1
    context["seed"] = effective
    context["_rng"] = np.random.default_rng(effective)
    random.seed(effective)
    np.random.seed(int(np.random.SeedSequence(effective).generate_state(1)[0]))
    return effective
