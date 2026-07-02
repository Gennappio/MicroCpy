"""
Population — the collective over agents, wrapping ``CellPopulation``.

Owns the agents (as Cells in a wrapped CellPopulation) and bridges them to the
World's occupancy index. It is where activation order lives (``ask``) and where
structural change is committed (``cull``) — individual agents only *request*
death; the Population enacts it. Per the read/write discipline, this is the only
place agents appear or disappear, and the collective never decides *for* an
agent — it places them, commits their decisions, and observes.

A Population can hold several agent **kinds**, each with its own Setup/Step
behaviours and trait params; ``run_agent_step`` asks each kind's agents with
that kind's Step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, List, Optional

import numpy as np

from src.abm.agent import Agent
from src.abm.world import Position, World

if TYPE_CHECKING:
    from src.abm.domain import Domain


class Population:
    """Collective over agents. Wraps CellPopulation; binds occupancy to the World."""

    def __init__(self, world: World, config=None, context: Optional[dict] = None, seed: int = 0):
        from src.biology.population import CellPopulation

        self.world = world
        self.domain: Optional["Domain"] = None  # set by the model builder
        self.params: dict = {}
        self._rng = np.random.default_rng(seed if seed else None)
        self.cellpop = CellPopulation(
            grid_size=(world.nx, world.ny),
            gene_network=None,
            custom_functions_module=None,
            config=config,
            context=context if context is not None else {},
        )
        # The live occupancy dict the World reads; Population owns the writes.
        self.world.bind_occupancy(self.cellpop.state.spatial_grid)

        # Per-step census history (opt-in: only populated when a reporting node
        # calls record_census). Each entry: {"step", "count", "by_kind"}.
        self.history: List[Dict] = []

        # Agent kinds: name -> {"setup", "step", "params"}.
        self.kinds: Dict[str, Dict] = {}
        # Collective behaviours (thin: placement + cull/census, never agent-regulating).
        self._collective_setup: Optional[Callable] = None
        self._collective_step: Optional[Callable] = None

    # behaviour binding -------------------------------------------------------
    def add_kind(self, name: str, setup: Optional[Callable] = None,
                 step: Optional[Callable] = None, params: Optional[Dict] = None) -> "Population":
        self.kinds[name] = {"setup": setup, "step": step, "params": params or {}}
        return self

    def on_setup(self, fn): self._collective_setup = fn; return self
    def on_step(self, fn): self._collective_step = fn; return self

    # creation ----------------------------------------------------------------
    def spawn(self, pos: Position, kind: Optional[str] = None, **state) -> Optional[Agent]:
        pos = self.world.normalize(pos)
        if not self.cellpop.add_cell(pos, phenotype="normal"):
            return None
        self._rebind()
        cell = self.cellpop.state.cells[self.cellpop.state.spatial_grid[pos]]
        if kind is not None:
            cell.state.metabolic_state["_kind"] = kind
        cell.state.metabolic_state.update(state)
        return Agent(cell, self)

    def populate(self, kind: str, n: int, **state_fn_or_const) -> int:
        """Place up to n agents of ``kind`` on random empty tiles. Trait values
        may be callables ``f(rng) -> value`` or constants."""
        placed = 0
        for _ in range(min(int(n), self.world.nx * self.world.ny)):
            pos = self.world.random_position(self._rng, empty=True)
            if pos is None:
                break
            state = {k: (v(self._rng) if callable(v) else v) for k, v in state_fn_or_const.items()}
            if self.spawn(pos, kind=kind, **state):
                placed += 1
        return placed

    def _rebind(self) -> None:
        """CellPopulation.add_cell swaps its state dicts (immutable pattern);
        re-point the World at the current live occupancy dict."""
        self.world.bind_occupancy(self.cellpop.state.spatial_grid)

    # access ------------------------------------------------------------------
    def agents(self) -> List[Agent]:
        return [Agent(c, self) for c in self.cellpop.state.cells.values()]

    def agents_of_kind(self, kind: str) -> List[Agent]:
        return [Agent(c, self) for c in self.cellpop.state.cells.values()
                if c.state.metabolic_state.get("_kind") == kind]

    def agent_by_id(self, cid: str) -> Optional[Agent]:
        cell = self.cellpop.state.cells.get(cid)
        return Agent(cell, self) if cell is not None else None

    def count(self) -> int:
        return len(self.cellpop.state.cells)

    def count_by_kind(self) -> Dict:
        out: Dict = {}
        for c in self.cellpop.state.cells.values():
            k = c.state.metabolic_state.get("_kind", "?")
            out[k] = out.get(k, 0) + 1
        return out

    def census(self) -> Dict:
        return {"count": self.count(), "by_kind": self.count_by_kind()}

    def snapshot(self) -> Dict[str, tuple]:
        """Agent positions grouped by kind: ``{kind: (xs, ys)}`` (parallel lists).
        The structured form a plotter needs to scatter agents by kind without
        re-iterating and unpacking positions by hand."""
        out: Dict[str, list] = {}
        for c in self.cellpop.state.cells.values():
            kind = c.state.metabolic_state.get("_kind", "?")
            xs_ys = out.setdefault(kind, ([], []))
            pos = c.state.position
            xs_ys[0].append(pos[0])
            xs_ys[1].append(pos[1])
        return {k: (list(xs), list(ys)) for k, (xs, ys) in out.items()}

    def record_census(self, step: Optional[int] = None) -> Dict:
        """Append the current census to ``self.history`` and return it. Opt-in —
        call once per step from a reporting node to build a population-over-time
        series (nothing accumulates otherwise)."""
        snapshot = {"step": step, **self.census()}
        self.history.append(snapshot)
        return snapshot

    # movement (the only writer of occupancy) ---------------------------------
    def relocate(self, agent: Agent, pos: Position) -> None:
        occ = self.cellpop.state.spatial_grid
        cell = agent._cell
        old = cell.state.position
        if occ.get(old) == cell.state.id:
            del occ[old]
        cell.state.position = pos
        occ[pos] = cell.state.id

    # activation (NetLogo `ask`) ---------------------------------------------
    def ask(self, env, fn: Callable, agents: Optional[List[Agent]] = None, order: str = "random") -> None:
        agents = self.agents() if agents is None else agents
        if order == "random":
            self._rng.shuffle(agents)
        for a in agents:
            if a.is_alive():
                env.set_agent(a)
                fn(env)
        env.set_agent(None)

    def run_setup(self, env) -> None:
        if self._collective_setup:
            self._collective_setup(env)
        for name, k in self.kinds.items():
            if k["setup"]:
                env.set_kind(name, k["params"])
                k["setup"](env)
        env.set_kind(None, {})

    def run_agent_step(self, env, order: str = "random") -> None:
        for name, k in self.kinds.items():
            if k["step"]:
                env.set_kind(name, k["params"])
                self.ask(env, k["step"], agents=self.agents_of_kind(name), order=order)
        env.set_kind(None, {})

    def run_collective_step(self, env) -> None:
        if self._collective_step:
            self._collective_step(env)

    # structural change (commit deaths) --------------------------------------
    def cull(self, predicate: Optional[Callable[[Agent], bool]] = None) -> int:
        occ = self.cellpop.state.spatial_grid
        cells = self.cellpop.state.cells
        gene_networks = self.cellpop.context.get("gene_networks", {})
        doomed = []
        for c in list(cells.values()):
            agent = Agent(c, self)
            if (not agent.is_alive()) or (predicate is not None and predicate(agent)):
                doomed.append(c)
        for c in doomed:
            pos = c.state.position
            if occ.get(pos) == c.state.id:
                del occ[pos]
            cells.pop(c.state.id, None)
            gene_networks.pop(c.state.id, None)
        return len(doomed)
