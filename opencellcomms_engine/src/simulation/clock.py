"""SimulationClock — single source of truth for step/time/dt.

The clock is owned by the engine (or by configure_time_and_steps in
workflow-only mode).  It is placed into the context as context['clock']
once and never re-bound.  Workflow functions read step/time/dt through
the clock; only the engine mutates clock.step.
"""

from dataclasses import dataclass


@dataclass
class SimulationClock:
    dt: float
    num_steps: int
    step: int = 0

    @property
    def time(self) -> float:
        """Current simulation time (step * dt)."""
        return self.step * self.dt

    def advance(self) -> None:
        """Increment step by 1."""
        self.step += 1

    def reset(self) -> None:
        """Reset step to 0."""
        self.step = 0
