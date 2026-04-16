"""
PhysiBoss Cycle Model - Stochastic cell-cycle phase transitions.

Python reimplementation of PhysiCell's Cycle_Model::advance_model().
Supports both fixed-duration and stochastic transitions between phases.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Phase:
    """A single cell-cycle phase."""
    name: str = ""
    index: int = 0
    duration: float = 0.0          # expected duration (1/rate) in minutes
    fixed_duration: bool = False   # if True, transition after exactly `duration`
    division_at_exit: bool = False # trigger division when leaving this phase
    removal_at_exit: bool = False  # remove cell when leaving this phase


@dataclass
class CycleModel:
    """
    Stochastic cell-cycle model matching PhysiCell's Cycle_Model.

    Manages phase transitions for a single cell.  Each cell gets its own
    CycleModel instance so that elapsed time is tracked individually.

    Transition logic (per dt):
    - Fixed duration: advance if elapsed >= duration
    - Stochastic:     advance with probability rate*dt  (rate = 1/duration)
    """
    phases: List[Phase] = field(default_factory=list)
    current_phase_index: int = 0
    elapsed_time: float = 0.0   # time in current phase (minutes)

    def advance(self, dt: float) -> Tuple[bool, bool]:
        """
        Advance the cycle model by dt minutes.

        Returns:
            (should_divide, should_remove) — flags indicating cell events.
        """
        if not self.phases:
            return False, False

        self.elapsed_time += dt
        phase = self.phases[self.current_phase_index]

        should_divide = False
        should_remove = False

        # Check transition
        transition = False
        if phase.fixed_duration:
            if self.elapsed_time >= phase.duration:
                transition = True
        else:
            # Stochastic transition: rate = 1/duration (if duration > 0)
            if phase.duration > 0:
                rate = 1.0 / phase.duration
                prob = 1.0 - math.exp(-rate * dt)
                if random.random() < prob:
                    transition = True
            # duration == 0 means instant transition
            elif phase.duration == 0:
                transition = True

        if transition:
            # Check for division/removal at phase exit
            if phase.division_at_exit:
                should_divide = True
            if phase.removal_at_exit:
                should_remove = True

            # Move to next phase (wrapping around)
            self.current_phase_index = (self.current_phase_index + 1) % len(self.phases)
            self.elapsed_time = 0.0

        return should_divide, should_remove

    def reset(self):
        """Reset the cycle model (e.g. after division)."""
        self.current_phase_index = 0
        self.elapsed_time = 0.0

    @classmethod
    def from_config(cls, cycle_config) -> "CycleModel":
        """
        Create a CycleModel from a CycleConfig dataclass.

        Maps PhysiCell cycle model names to phase definitions.
        """
        phases = []

        if cycle_config.phase_durations:
            for i, dur in enumerate(cycle_config.phase_durations):
                phase = Phase(
                    name=f"phase_{i}",
                    index=i,
                    duration=dur,
                    fixed_duration=(dur > 0),
                )
                phases.append(phase)
        elif cycle_config.phase_transition_rates:
            for i, rate in enumerate(cycle_config.phase_transition_rates):
                dur = 1.0 / rate if rate > 0 else 0.0
                phase = Phase(
                    name=f"phase_{i}",
                    index=i,
                    duration=dur,
                    fixed_duration=False,
                )
                phases.append(phase)

        if not phases:
            # Default: simple Ki67 basic model (two phases)
            phases = [
                Phase(name="Ki67-", index=0, duration=480.0, fixed_duration=False),
                Phase(name="Ki67+", index=1, duration=480.0, fixed_duration=False,
                      division_at_exit=True),
            ]

        return cls(phases=phases)

    def copy(self) -> "CycleModel":
        """Create an independent copy (for daughter cells)."""
        import copy
        return copy.deepcopy(self)
