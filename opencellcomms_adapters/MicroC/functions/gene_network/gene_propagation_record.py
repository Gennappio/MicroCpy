"""The published gene-propagation step count, and the clock derived from it.

One scheduler iteration advances every cell's Boolean network by
``propagation_steps`` single-gene updates (the Propagate Gene Networks nodes).
Two runs with different step counts are therefore not comparable per scheduler
iteration; the comparable clock is the number of gene-network updates a cell
has received,

    gene_steps = scheduler iteration x propagation_steps

The Propagation Steps parameter node on the gene_update canvas owns that number
(docs/READABILITY.md R2.2). The updater publishes it here on every call; the
per-iteration reporters read it back for their ``gene_steps`` column and the
time axis of their plots, and never carry a copy of it.
"""

from typing import Optional

from src.biology.context import BiologicalContext

GENE_PROPAGATION_KEY = "gene_propagation"


def publish_propagation_steps(env: BiologicalContext, propagation_steps: int,
                              updater: str) -> None:
    """Record the step count in effect (called by the updater on every pass)."""
    env.results.store(GENE_PROPAGATION_KEY, {
        "propagation_steps": int(propagation_steps),
        "updater": updater,
    })


def published_propagation_steps(env: BiologicalContext) -> Optional[int]:
    """The step count the updater published, or None when no updater has run."""
    record = env.results.get(GENE_PROPAGATION_KEY)
    if not isinstance(record, dict) or record.get("propagation_steps") is None:
        return None
    try:
        return int(record["propagation_steps"])
    except (TypeError, ValueError):
        return None


def gene_steps(env: BiologicalContext, iteration: int) -> Optional[int]:
    """Gene-network updates per cell after ``iteration`` scheduler steps, or None."""
    steps = published_propagation_steps(env)
    return iteration * steps if steps is not None else None
