"""
BiologicalContext — typed authoring layer for OpenCellComms workflow functions.

Functions opt in by typing their first argument as `env: BiologicalContext`.
The executor introspects the signature and constructs the env from the raw context dict.

Old functions with `context: Dict[str, Any]` keep working unchanged.

Design contract:
    - Phenotype mutations go through typed methods (cell.mark_necrotic()), not string assignment.
    - Coordinate conversion for substance lookups lives once, in EnvironmentView.
    - The escape hatch (env.raw_context) returns the underlying dict for unusual cases.
"""

from __future__ import annotations

from enum import Enum
from typing import (
    Any, Dict, Iterator, List, Optional, Tuple, Union, TYPE_CHECKING
)

if TYPE_CHECKING:
    from src.biology.cell import Cell
    from src.biology.population import CellPopulation
    from src.biology.gene_network import BooleanNetwork, NetworkNode
    from src.interfaces.base import ISubstanceSimulator


Position = Union[Tuple[int, int], Tuple[int, int, int], Tuple[float, ...]]


class KernelContractError(RuntimeError):
    """Raised when a typed view is used but the capability backing it is absent.

    Almost always means the function accessed (e.g.) ``env.cells`` without
    declaring ``requires=['population']``, or is running under a kernel that does
    not provide that capability. Failing loudly here beats silently returning
    empty results that produce wrong science downstream.
    """


def _missing_capability(token: str, accessor: str) -> 'KernelContractError':
    return KernelContractError(
        f"{accessor} was used but the simulation context provides no '{token}'. "
        f"Declare requires=['{token}'] on this function and run it under a kernel "
        f"that provides '{token}' (e.g. the biophysics kernel)."
    )


class Phenotype(str, Enum):
    """Cell fate values.

    Inherits from str so `cell.state.phenotype == 'Necrosis'` keeps working
    in legacy code paths during migration.
    """
    NECROSIS = 'Necrosis'
    APOPTOSIS = 'Apoptosis'
    PROLIFERATION = 'Proliferation'
    GROWTH_ARREST = 'Growth_Arrest'
    QUIESCENT = 'Quiescent'


class GeneNode:
    """Typed wrapper over a NetworkNode in a cell's gene network."""

    def __init__(self, node: 'NetworkNode'):
        self._node = node

    def is_on(self) -> bool:
        return bool(self._node.current_state)

    def is_off(self) -> bool:
        return not self._node.current_state

    def turn_on(self) -> None:
        self._node.current_state = True

    def turn_off(self) -> None:
        self._node.current_state = False

    def set(self, value: bool) -> None:
        self._node.current_state = bool(value)

    @property
    def name(self) -> str:
        return self._node.name


class CellHandle:
    """Typed wrapper over engine Cell. All mutations go through methods."""

    def __init__(self, cell: 'Cell', env: 'BiologicalContext'):
        self._cell = cell
        self._env = env

    @property
    def raw(self) -> 'Cell':
        """Underlying engine Cell. Escape hatch for code that needs direct access."""
        return self._cell

    @property
    def id(self) -> str:
        return self._cell.state.id

    @property
    def position(self) -> Position:
        return self._cell.state.position

    @property
    def phenotype(self) -> str:
        return self._cell.state.phenotype

    @property
    def age(self) -> float:
        return self._cell.state.age

    @property
    def division_count(self) -> int:
        return self._cell.state.division_count

    @property
    def gene_states(self) -> Dict[str, bool]:
        """Snapshot of last-known gene states stored on cell.state."""
        return dict(self._cell.state.gene_states)

    # --- Phenotype mutations -------------------------------------------------

    def set_phenotype(self, p: Union[Phenotype, str]) -> None:
        value = p.value if isinstance(p, Phenotype) else str(p)
        self._cell.state = self._cell.state.with_updates(phenotype=value)

    def mark_necrotic(self) -> None:
        self.set_phenotype(Phenotype.NECROSIS)

    def mark_apoptotic(self) -> None:
        self.set_phenotype(Phenotype.APOPTOSIS)

    def mark_proliferating(self) -> None:
        self.set_phenotype(Phenotype.PROLIFERATION)

    def mark_growth_arrested(self) -> None:
        self.set_phenotype(Phenotype.GROWTH_ARREST)

    def mark_quiescent(self) -> None:
        self.set_phenotype(Phenotype.QUIESCENT)

    def set_age(self, hours: float) -> None:
        self._cell.state = self._cell.state.with_updates(age=float(hours))

    def set_gene_state_snapshot(self, gene_states: Dict[str, bool]) -> None:
        """Write the cell's `gene_states` snapshot dict on CellState."""
        self._cell.state = self._cell.state.with_updates(gene_states=dict(gene_states))

    # --- Phenotype queries ---------------------------------------------------

    @property
    def is_necrotic(self) -> bool:
        return self._cell.state.phenotype == Phenotype.NECROSIS.value

    @property
    def is_apoptotic(self) -> bool:
        return self._cell.state.phenotype == Phenotype.APOPTOSIS.value

    @property
    def is_proliferating(self) -> bool:
        return self._cell.state.phenotype == Phenotype.PROLIFERATION.value

    @property
    def is_growth_arrested(self) -> bool:
        return self._cell.state.phenotype == Phenotype.GROWTH_ARREST.value

    @property
    def is_quiescent(self) -> bool:
        return self._cell.state.phenotype == Phenotype.QUIESCENT.value

    # --- Gene access ---------------------------------------------------------

    def gene(self, name: str) -> Optional[GeneNode]:
        """Access a gene node in this cell's gene network.

        Returns None if the cell has no gene network or the gene doesn't exist.
        """
        network = self._env._gene_network_for(self._cell.state.id)
        if network is None:
            return None
        node = network.nodes.get(name)
        if node is None:
            return None
        return GeneNode(node)

    def has_gene(self, name: str) -> bool:
        network = self._env._gene_network_for(self._cell.state.id)
        return network is not None and name in network.nodes

    def __repr__(self) -> str:
        return f"CellHandle({self.id[:8]}, pos={self.position}, phenotype={self.phenotype})"


class PopulationView:
    """Iterable view over the cell population."""

    def __init__(self, env: 'BiologicalContext'):
        self._env = env

    def _population(self) -> Optional['CellPopulation']:
        return self._env._ctx.get('population')

    def _require_population(self) -> 'CellPopulation':
        pop = self._population()
        if pop is None:
            raise _missing_capability('population', 'env.cells')
        return pop

    def __iter__(self) -> Iterator[CellHandle]:
        pop = self._require_population()
        return (CellHandle(c, self._env) for c in pop.state.cells.values())

    def __len__(self) -> int:
        return len(self._require_population().state.cells)

    def by_id(self, cell_id: str) -> Optional[CellHandle]:
        pop = self._require_population()
        cell = pop.state.cells.get(cell_id)
        return CellHandle(cell, self._env) if cell is not None else None

    def by_phenotype(self, p: Union[Phenotype, str]) -> Iterator[CellHandle]:
        value = p.value if isinstance(p, Phenotype) else str(p)
        return (c for c in self if c.phenotype == value)

    def add(self,
            position: Position,
            phenotype: Union[Phenotype, str] = Phenotype.GROWTH_ARREST) -> bool:
        pop = self._require_population()
        value = phenotype.value if isinstance(phenotype, Phenotype) else str(phenotype)
        return pop.add_cell(position, value)

    def statistics(self) -> Dict[str, Any]:
        return self._require_population().get_population_statistics()

    @property
    def raw(self) -> Optional['CellPopulation']:
        """Underlying CellPopulation. Escape hatch."""
        return self._population()


class EnvironmentView:
    """Substance concentration queries. Owns coordinate conversion."""

    def __init__(self, env: 'BiologicalContext'):
        self._env = env
        self._cached_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None

    def _simulator(self) -> Optional['ISubstanceSimulator']:
        return self._env._ctx.get('simulator')

    def _config(self) -> Any:
        return self._env._ctx.get('config')

    def _concentrations(self) -> Dict[str, Dict[Tuple[int, int], float]]:
        if self._cached_concentrations is None:
            sim = self._simulator()
            if sim is None:
                raise _missing_capability('simulator', 'env.environment / env.concentration')
            else:
                try:
                    self._cached_concentrations = sim.get_substance_concentrations()
                except Exception as e:
                    print(f"[BiologicalContext] failed to read substance concentrations: {e}")
                    self._cached_concentrations = {}
        return self._cached_concentrations

    def invalidate_cache(self) -> None:
        """Drop the cached concentration snapshot. Call after simulator.update()."""
        self._cached_concentrations = None

    def all_substances(self) -> List[str]:
        return list(self._concentrations().keys())

    def concentration(self,
                      substance: str,
                      at: Union[CellHandle, Position, 'Cell']) -> float:
        """Concentration of a substance at a cell or position.

        Handles cell logical position → grid index conversion.
        Returns 0.0 if substance is unknown or position is out of range.
        """
        position = self._position_of(at)
        concs = self._concentrations()
        grid = concs.get(substance)
        if grid is None:
            # Try case-insensitive fallback (legacy code uses 'oxygen' vs 'Oxygen')
            for name, g in concs.items():
                if name.lower() == substance.lower():
                    grid = g
                    break
        if not grid:
            return 0.0
        grid_pos = self._to_grid_index(position, grid)
        if grid_pos in grid:
            return grid[grid_pos]
        # Fallback: try raw position
        raw = tuple(position[:2])
        return grid.get(raw, 0.0)

    def concentrations_at(self,
                          at: Union[CellHandle, Position, 'Cell']) -> Dict[str, float]:
        """All substance concentrations at a cell or position."""
        position = self._position_of(at)
        concs = self._concentrations()
        out: Dict[str, float] = {}
        if not concs:
            return out
        # Use any substance grid to derive grid dimensions (consistent across substances)
        first_grid = next(iter(concs.values()))
        grid_pos = self._to_grid_index(position, first_grid)
        for substance_name, grid in concs.items():
            if grid_pos in grid:
                out[substance_name] = grid[grid_pos]
            else:
                raw = tuple(position[:2])
                out[substance_name] = grid.get(raw, 0.0)
        return out

    def summary(self) -> Dict[str, Dict[str, float]]:
        sim = self._simulator()
        if sim is None:
            raise _missing_capability('simulator', 'env.environment.summary')
        try:
            return sim.get_summary_statistics()
        except Exception:
            return {}

    @property
    def raw_simulator(self) -> Optional['ISubstanceSimulator']:
        """Underlying ISubstanceSimulator. Escape hatch."""
        return self._simulator()

    # --- Internal: position resolution ---------------------------------------

    def _position_of(self, at: Union[CellHandle, Position, 'Cell']) -> Tuple[float, ...]:
        if isinstance(at, CellHandle):
            return at.position
        # Engine Cell — duck-typed (avoid runtime import cycle)
        if hasattr(at, 'state') and hasattr(at.state, 'position'):
            return at.state.position
        if isinstance(at, tuple):
            return at
        raise TypeError(f"Cannot resolve position from {type(at).__name__}")

    def _to_grid_index(self,
                       position: Tuple[float, ...],
                       reference_grid: Dict[Tuple[int, int], float]) -> Tuple[int, int]:
        """Convert cell logical position → grid index.

        Logic lifted from MicroC mark_necrotic_cells._get_local_environment.
        Uses config.domain when available; otherwise heuristic scaling.
        """
        if not reference_grid:
            return (0, 0)

        max_grid_x = max(pos[0] for pos in reference_grid.keys())
        max_grid_y = max(pos[1] for pos in reference_grid.keys())
        nx = max_grid_x + 1
        ny = max_grid_y + 1

        cell_x = position[0]
        cell_y = position[1]

        config = self._config()
        if config is not None and hasattr(config, 'domain'):
            domain = config.domain
            domain_size_um = (
                domain.size_x.micrometers
                if hasattr(domain.size_x, 'micrometers')
                else domain.size_x
            )
            cell_size_um = 20.0
            if hasattr(domain, 'cell_height'):
                ch = domain.cell_height
                cell_size_um = ch.micrometers if hasattr(ch, 'micrometers') else float(ch)
            phys_x = cell_x * cell_size_um
            phys_y = cell_y * cell_size_um
            grid_spacing = domain_size_um / nx if nx > 0 else 1.0
            grid_x = int(phys_x / grid_spacing) if grid_spacing > 0 else int(cell_x)
            grid_y = int(phys_y / grid_spacing) if grid_spacing > 0 else int(cell_y)
        else:
            if cell_x > nx or cell_y > ny:
                scale = max(cell_x, cell_y) / max(nx, ny) if max(cell_x, cell_y) > 0 else 1.0
                scale = max(1.0, scale)
                grid_x = int(cell_x / scale)
                grid_y = int(cell_y / scale)
            else:
                grid_x = int(cell_x)
                grid_y = int(cell_y)

        grid_x = max(0, min(nx - 1, grid_x))
        grid_y = max(0, min(ny - 1, grid_y))
        return (grid_x, grid_y)


class ResultsView:
    """Typed result sink. Replaces ad-hoc context['results'] / context['changes']."""

    def __init__(self, env: 'BiologicalContext'):
        self._env = env

    def store(self, key: str, value: Any) -> None:
        results = self._env._ctx.setdefault('results', {})
        results[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._env._ctx.get('results', {}).get(key, default)

    def record_change(self, category: str, payload: Dict[str, Any]) -> None:
        changes = self._env._ctx.setdefault('changes', {})
        changes[category] = payload

    def get_change(self, category: str) -> Optional[Dict[str, Any]]:
        return self._env._ctx.get('changes', {}).get(category)


class BiologicalContext:
    """Root typed context passed as `env` to opted-in workflow functions.

    Wraps the raw context dict. All views (cells, environment, results)
    read and write through the same underlying dict, so mutations propagate
    to other functions (typed or legacy) sharing the same workflow run.
    """

    def __init__(self, raw_context: Dict[str, Any]):
        if raw_context is None:
            raw_context = {}
        self._ctx = raw_context
        self._cells_view: Optional[PopulationView] = None
        self._env_view: Optional[EnvironmentView] = None
        self._results_view: Optional[ResultsView] = None
        # Per-agent / per-kind state lives in the shared context dict (not on the
        # env instance) because the executor builds a fresh env for every node;
        # the per-agent "ask" sets these so each node's env sees the current agent.

    @property
    def cells(self) -> PopulationView:
        if self._cells_view is None:
            self._cells_view = PopulationView(self)
        return self._cells_view

    @property
    def environment(self) -> EnvironmentView:
        if self._env_view is None:
            self._env_view = EnvironmentView(self)
        return self._env_view

    @property
    def results(self) -> ResultsView:
        if self._results_view is None:
            self._results_view = ResultsView(self)
        return self._results_view

    def concentration(self,
                      substance: str,
                      at: Union[CellHandle, Position, 'Cell']) -> float:
        """Shortcut for `env.environment.concentration(...)`."""
        return self.environment.concentration(substance, at)

    def concentrations_at(self,
                          at: Union[CellHandle, Position, 'Cell']) -> Dict[str, float]:
        return self.environment.concentrations_at(at)

    @property
    def step(self) -> int:
        clock = self._ctx.get('clock')
        if clock is not None and hasattr(clock, 'step'):
            return int(clock.step)
        return int(self._ctx.get('current_step', self._ctx.get('step', 0)))

    @property
    def dt(self) -> float:
        clock = self._ctx.get('clock')
        if clock is not None and hasattr(clock, 'dt'):
            return float(clock.dt)
        return float(self._ctx.get('dt', 1.0))

    @property
    def config(self) -> Any:
        return self._ctx.get('config')

    @property
    def verbose(self) -> bool:
        return bool(self._ctx.get('verbose', False))

    # --- ABM class layer (World / Domain / Population / Resource / Agent) -----
    # These surface the typed ABM objects to behaviour authors. They read the
    # raw context where the model builder stored them.

    @property
    def domain(self):
        """The ABM Domain (owns the World and Resources)."""
        return self._ctx.get('domain')

    @property
    def world(self):
        """The active World (from the Domain, or a bare 'world' in context)."""
        domain = self._ctx.get('domain')
        return domain.world if domain is not None else self._ctx.get('world')

    @property
    def population(self):
        """The ABM Population wrapper (distinct from the raw CellPopulation)."""
        return self._ctx.get('abm_population')

    def resource(self, name: str):
        """The named Resource field on the Domain."""
        domain = self._ctx.get('domain')
        if domain is None:
            raise KeyError("No 'domain' in context — build the model first")
        return domain.resource(name)

    @property
    def current_resource(self):
        """The resource currently being stepped by a resource behaviour call."""
        return self._ctx.get('_current_resource')

    @property
    def agents(self):
        """All ABM agents (empty list if no ABM population is present)."""
        pop = self._ctx.get('abm_population')
        return pop.agents() if pop is not None else []

    @property
    def agent(self):
        """The agent currently being asked (set by the per-agent loop), else None."""
        return self._ctx.get('_current_agent')

    @property
    def cell(self):
        """The single cell currently being asked in a LEGACY per-cell loop, as a
        CellHandle, else None.

        For models that run on the legacy CellPopulation (e.g. MicroC, FiPy
        diffusion) there is no abm_population to bind as env.agent; the executor's
        per-cell ask binds context['_current_cell'] instead. A function is then
        per-cell when env.cell is set, and falls back to looping env.cells when it
        is None — so the same function works under both calling conventions.
        """
        c = self._ctx.get('_current_cell')
        return CellHandle(c, self) if c is not None else None

    def set_agent(self, agent) -> None:
        self._ctx['_current_agent'] = agent

    # --- Intent queue --------------------------------------------------------

    @property
    def intents(self) -> Dict[str, List[Dict[str, Any]]]:
        """Pending model-change requests for the reconciliation phase."""
        return self._ctx.setdefault('_intents', {})

    def emit_intent(self, kind: str, **payload: Any) -> None:
        """Append a typed intent without committing shared state immediately."""
        self.intents.setdefault(kind, []).append(payload)

    def request_move(self, agent_id: Optional[str] = None, target: Optional[Position] = None, **payload: Any) -> None:
        agent = self.agent
        resolved_agent_id = agent_id or (agent.id if agent is not None else None)
        if resolved_agent_id is None:
            raise ValueError("request_move needs agent_id or a current env.agent")
        if target is None:
            raise ValueError("request_move needs a target position")
        self.emit_intent('move', agent_id=resolved_agent_id, target=target, **payload)

    def request_remove_agent(self, agent_id: Optional[str] = None, reason: str = "", **payload: Any) -> None:
        agent = self.agent
        resolved_agent_id = agent_id or (agent.id if agent is not None else None)
        if resolved_agent_id is None:
            raise ValueError("request_remove_agent needs agent_id or a current env.agent")
        self.emit_intent('remove_agent', agent_id=resolved_agent_id, reason=reason, **payload)

    def request_add_agent(self, kind: Optional[str] = None, position: Optional[Position] = None, state: Optional[Dict[str, Any]] = None, **payload: Any) -> None:
        if position is None:
            raise ValueError("request_add_agent needs a position")
        self.emit_intent('add_agent', kind=kind, position=position, state=state or {}, **payload)

    def request_resource_delta(self, resource: str, amount: float, position: Optional[Position] = None, **payload: Any) -> None:
        agent = self.agent
        resolved_position = position if position is not None else (agent.position if agent is not None else None)
        if resolved_position is None:
            raise ValueError("request_resource_delta needs position or a current env.agent")
        self.emit_intent('resource_delta', resource=resource, amount=float(amount), position=resolved_position, **payload)

    def request_consume_resource(self, resource: str, amount: Optional[float] = None, agent_id: Optional[str] = None,
                                 position: Optional[Position] = None, store_as: Optional[str] = None, **payload: Any) -> None:
        agent = self.agent
        resolved_agent_id = agent_id or (agent.id if agent is not None else None)
        resolved_position = position if position is not None else (agent.position if agent is not None else None)
        if resolved_agent_id is None or resolved_position is None:
            raise ValueError("request_consume_resource needs an agent and a position")
        self.emit_intent(
            'consume_resource',
            resource=resource,
            amount=amount,
            agent_id=resolved_agent_id,
            position=resolved_position,
            store_as=store_as or resource,
            **payload
        )

    def clear_intents(self) -> None:
        self._ctx['_intents'] = {}

    @property
    def kind(self):
        """The agent kind currently being set up / stepped, else None."""
        return self._ctx.get('_current_kind')

    @property
    def kind_params(self) -> Dict[str, Any]:
        """Params (count + traits) of the current agent kind."""
        return self._ctx.get('_current_kind_params', {})

    def set_kind(self, name, params=None) -> None:
        self._ctx['_current_kind'] = name
        self._ctx['_current_kind_params'] = params or {}

    def gene_network(self, cell: Union[CellHandle, 'Cell', str]) -> Optional['BooleanNetwork']:
        """Get the BooleanNetwork for a cell (or cell id).

        Returns the underlying engine network for code that needs direct access
        (graph walking, .step(), input-state initialization, etc.).
        """
        cell_id = self._cell_id(cell)
        return self._gene_network_for(cell_id)

    def set_gene_network(self,
                         cell: Union[CellHandle, 'Cell', str],
                         network: 'BooleanNetwork') -> None:
        cell_id = self._cell_id(cell)
        networks = self._ctx.setdefault('gene_networks', {})
        networks[cell_id] = network

    def remove_gene_network(self, cell: Union[CellHandle, 'Cell', str]) -> None:
        cell_id = self._cell_id(cell)
        networks = self._ctx.get('gene_networks')
        if networks and cell_id in networks:
            del networks[cell_id]

    @property
    def raw_context(self) -> Dict[str, Any]:
        """Escape hatch. You are leaving the typed zone."""
        return self._ctx

    # --- Internal helpers ----------------------------------------------------

    def _gene_network_for(self, cell_id: str) -> Optional['BooleanNetwork']:
        networks = self._ctx.get('gene_networks')
        if not networks:
            return None
        return networks.get(cell_id)

    @staticmethod
    def _cell_id(cell: Union[CellHandle, 'Cell', str]) -> str:
        if isinstance(cell, str):
            return cell
        if isinstance(cell, CellHandle):
            return cell.id
        if hasattr(cell, 'state') and hasattr(cell.state, 'id'):
            return cell.state.id
        raise TypeError(f"Cannot resolve cell id from {type(cell).__name__}")


__all__ = [
    'BiologicalContext',
    'CellHandle',
    'GeneNode',
    'PopulationView',
    'EnvironmentView',
    'ResultsView',
    'Phenotype',
    'KernelContractError',
]
