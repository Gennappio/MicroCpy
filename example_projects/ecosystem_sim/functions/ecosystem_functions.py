"""
Ecosystem Simulation Functions
Agent-based predator-prey model functions for MicroC workflow system.
"""

import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Agent:
    """Base agent class with position and ID."""
    id: int
    x: int
    y: int
    
    def move(self, grid_size: int):
        """Move to a random adjacent cell."""
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
        self.x = (self.x + dx) % grid_size
        self.y = (self.y + dy) % grid_size


@dataclass  
class Prey(Agent):
    """Prey agent that can reproduce."""
    pass


@dataclass
class Predator(Agent):
    """Predator agent that hunts prey and can starve."""
    energy: int = 10  # Steps since last meal
    
    def eat(self):
        """Reset energy after eating."""
        self.energy = 0
    
    def is_starving(self, starve_time: int) -> bool:
        """Check if predator should die from starvation."""
        return self.energy >= starve_time


# =============================================================================
# INITIALIZATION Stage Functions
# =============================================================================

def create_grid(context, grid_size: int = None, **kwargs):
    """
    Create an empty NxN grid for the simulation.

    Args:
        context: Context dictionary
        grid_size: Size of grid (uses params.grid_size if not provided)

    Writes:
        state.grid: 2D numpy array
    """
    ctx = context  # Use ctx as local alias for convenience
    size = grid_size or ctx.get('params.grid_size', 50)
    grid = np.zeros((size, size), dtype=int)
    ctx['state.grid'] = grid
    print(f"[INIT] Created {size}x{size} grid")
    return grid


def spawn_prey(context, count: int = None, **kwargs):
    """
    Spawn initial prey population at random positions.

    Args:
        context: Context dictionary
        count: Number of prey (uses params.initial_prey if not provided)

    Writes:
        state.prey: List of Prey agents
    """
    ctx = context
    n = count or ctx.get('params.initial_prey', 100)
    grid_size = ctx.get('params.grid_size', 50)

    prey_list = []
    for i in range(n):
        prey = Prey(
            id=i,
            x=random.randint(0, grid_size - 1),
            y=random.randint(0, grid_size - 1)
        )
        prey_list.append(prey)

    ctx['state.prey'] = prey_list
    print(f"[INIT] Spawned {n} prey agents")
    return prey_list


def spawn_predators(context, count: int = None, **kwargs):
    """
    Spawn initial predator population at random positions.

    Args:
        context: Context dictionary
        count: Number of predators (uses params.initial_predators if not provided)

    Writes:
        state.predators: List of Predator agents
    """
    ctx = context
    n = count or ctx.get('params.initial_predators', 20)
    grid_size = ctx.get('params.grid_size', 50)

    predator_list = []
    for i in range(n):
        predator = Predator(
            id=i,
            x=random.randint(0, grid_size - 1),
            y=random.randint(0, grid_size - 1),
            energy=0
        )
        predator_list.append(predator)

    ctx['state.predators'] = predator_list
    print(f"[INIT] Spawned {n} predator agents")
    return predator_list


def initialize_history(context, **kwargs):
    """
    Initialize the population history tracker.

    Writes:
        output.population_history: Empty list
        state.current_step: 0
    """
    ctx = context
    ctx['output.population_history'] = []
    ctx['state.current_step'] = 0
    print("[INIT] Initialized population history tracker")


# =============================================================================
# SIMULATION Stage Functions
# =============================================================================

def move_all_agents(context, **kwargs):
    """
    Move all agents (predators and prey) to random adjacent cells.

    Reads:
        state.predators, state.prey, params.grid_size
    """
    ctx = context
    grid_size = ctx.get('params.grid_size', 50)

    for prey in ctx.get('state.prey', []):
        prey.move(grid_size)

    for predator in ctx.get('state.predators', []):
        predator.move(grid_size)
        predator.energy += 1  # Increment hunger


def handle_predation(context, **kwargs):
    """
    Handle predator-prey interactions. Predators eat prey in same cell.

    Reads:
        state.predators, state.prey, params.predation_rate, params.predator_reproduction_rate
    Writes:
        state.prey (removes eaten prey)
        state.predators (adds new predators from reproduction)
    """
    ctx = context
    predation_rate = ctx.get('params.predation_rate', 0.4)
    reproduction_rate = ctx.get('params.predator_reproduction_rate', 0.3)

    predators = ctx.get('state.predators', [])
    prey_list = ctx.get('state.prey', [])

    # Build spatial index of prey
    prey_by_cell = {}
    for p in prey_list:
        key = (p.x, p.y)
        if key not in prey_by_cell:
            prey_by_cell[key] = []
        prey_by_cell[key].append(p)

    eaten_prey = set()
    new_predators = []
    next_pred_id = max((p.id for p in predators), default=0) + 1

    for predator in predators:
        cell_prey = prey_by_cell.get((predator.x, predator.y), [])
        for prey in cell_prey:
            if prey.id not in eaten_prey and random.random() < predation_rate:
                eaten_prey.add(prey.id)
                predator.eat()

                # Chance to reproduce after eating
                if random.random() < reproduction_rate:
                    new_pred = Predator(
                        id=next_pred_id,
                        x=predator.x,
                        y=predator.y,
                        energy=0
                    )
                    new_predators.append(new_pred)
                    next_pred_id += 1
                break  # One prey per predator per step

    # Remove eaten prey
    ctx['state.prey'] = [p for p in prey_list if p.id not in eaten_prey]

    # Add new predators
    ctx['state.predators'] = predators + new_predators

    if eaten_prey:
        print(f"  [PREDATION] {len(eaten_prey)} prey eaten, {len(new_predators)} predators born")


def handle_prey_reproduction(context, **kwargs):
    """
    Handle prey reproduction. Each prey has a chance to reproduce.

    Reads:
        state.prey, params.prey_reproduction_rate
    Writes:
        state.prey (adds new prey)
    """
    ctx = context
    reproduction_rate = ctx.get('params.prey_reproduction_rate', 0.05)
    prey_list = ctx.get('state.prey', [])

    new_prey = []
    next_id = max((p.id for p in prey_list), default=0) + 1

    for prey in prey_list:
        if random.random() < reproduction_rate:
            new_p = Prey(id=next_id, x=prey.x, y=prey.y)
            new_prey.append(new_p)
            next_id += 1

    ctx['state.prey'] = prey_list + new_prey

    if new_prey:
        print(f"  [REPRODUCTION] {len(new_prey)} new prey born")


def handle_predator_starvation(context, **kwargs):
    """
    Remove predators that have starved.

    Reads:
        state.predators, params.predator_starve_time
    Writes:
        state.predators (removes starved predators)
    """
    ctx = context
    starve_time = ctx.get('params.predator_starve_time', 10)
    predators = ctx.get('state.predators', [])

    survivors = [p for p in predators if not p.is_starving(starve_time)]
    starved = len(predators) - len(survivors)

    ctx['state.predators'] = survivors

    if starved:
        print(f"  [STARVATION] {starved} predators died from hunger")


def record_population(context, **kwargs):
    """
    Record current population counts to history.

    Reads:
        state.predators, state.prey, state.current_step
    Writes:
        output.population_history (appends new record)
    """
    ctx = context
    step = ctx.get('state.current_step', 0)
    n_predators = len(ctx.get('state.predators', []))
    n_prey = len(ctx.get('state.prey', []))

    history = ctx.get('output.population_history', [])
    history.append({
        'step': step,
        'predators': n_predators,
        'prey': n_prey
    })
    ctx['output.population_history'] = history

    print(f"[STEP {step}] Predators: {n_predators}, Prey: {n_prey}")


def increment_step(context, **kwargs):
    """
    Increment the simulation step counter.

    Writes:
        state.current_step
    """
    ctx = context
    step = ctx.get('state.current_step', 0)
    ctx['state.current_step'] = step + 1


# =============================================================================
# OUTPUT Stage Functions
# =============================================================================

def save_results_csv(context, **kwargs):
    """
    Save population history to CSV file.

    Reads:
        output.population_history, results_dir
    """
    import os

    ctx = context
    results_dir = ctx.get('results_dir', 'results')
    history = ctx.get('output.population_history', [])

    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, 'population_history.csv')

    with open(csv_path, 'w') as f:
        f.write('step,predators,prey\n')
        for record in history:
            f.write(f"{record['step']},{record['predators']},{record['prey']}\n")

    print(f"[OUTPUT] Saved population history to {csv_path}")


def print_summary(context, **kwargs):
    """
    Print a summary of the simulation results.

    Reads:
        output.population_history, state.predators, state.prey
    """
    ctx = context
    history = ctx.get('output.population_history', [])

    if not history:
        print("[SUMMARY] No simulation data recorded")
        return

    initial = history[0]
    final = history[-1]

    print("\n" + "=" * 50)
    print("ECOSYSTEM SIMULATION SUMMARY")
    print("=" * 50)
    print(f"Total steps: {len(history)}")
    print(f"Initial population: {initial['predators']} predators, {initial['prey']} prey")
    print(f"Final population: {final['predators']} predators, {final['prey']} prey")

    # Find peak populations
    max_pred = max(h['predators'] for h in history)
    max_prey = max(h['prey'] for h in history)
    print(f"Peak predators: {max_pred}")
    print(f"Peak prey: {max_prey}")

    # Check for extinction
    if final['predators'] == 0:
        print("⚠️  PREDATOR EXTINCTION occurred!")
    if final['prey'] == 0:
        print("⚠️  PREY EXTINCTION occurred!")

    print("=" * 50 + "\n")

