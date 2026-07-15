export const KINDS = {
  COMPOSER: 'composer',
  SUBWORKFLOW: 'subworkflow',
  AGENT_CREATE: 'agent_create',
  AGENT_BEHAVIOR: 'agent_behavior',
  RESOURCE_INIT: 'resource_init',
  RESOURCE_BEHAVIOR: 'resource_behavior',
  WORLD: 'world',
  WORLD_BEHAVIOR: 'world_behavior',
  PROCESSING_BEHAVIOR: 'processing_behavior',
  SCHEDULER: 'scheduler',
  INIT_SEQUENCE: 'init_sequence',
};

export const MAIN_TABS = {
  OVERVIEW: 'overview',
  AGENTS: 'agents',
  RESOURCES: 'resources',
  WORLD: 'world',
  INITIALIZATION: 'initialization',
  SCHEDULER: 'scheduler',
  PLANNER: 'planner',
  PROCESSING: 'processing',
  RESULTS: 'results',
};

export const SCHEDULER_NAME = '__scheduler__';
export const INIT_SEQUENCE_NAME = '__init_sequence__';
export const WORLD_NAME = '__world__';

// The display label for a subworkflow's controller (init) node is ALWAYS derived
// from the subworkflow name — never stored or hand-edited — so it stays
// consistent and can't drift to an arbitrary value. Underscores become spaces,
// trimmed, uppercased: "sugar_growback" -> "SUGAR GROWBACK",
// "__scheduler__" -> "SCHEDULER".
export const controllerLabel = (name) =>
  String(name || '').replace(/_+/g, ' ').trim().toUpperCase();

export const BEHAVIOR_KINDS = new Set([
  KINDS.AGENT_BEHAVIOR,
  KINDS.RESOURCE_BEHAVIOR,
  KINDS.WORLD_BEHAVIOR,
  KINDS.PROCESSING_BEHAVIOR,
]);

// Kinds that represent an init canvas — used by the Initialization tab palette
// (only these are draggable into __init_sequence__) and by the Scheduler palette
// (which must explicitly EXCLUDE these).
export const INIT_KINDS = new Set([
  KINDS.RESOURCE_INIT,
  KINDS.WORLD,
]);

// All canvases where function nodes can be placed (everything except scheduler).
// Init canvases hold functions too (e.g. setup_population, setup_substances).
export const FUNCTION_HOSTING_KINDS = new Set([
  KINDS.AGENT_CREATE,
  KINDS.AGENT_BEHAVIOR,
  KINDS.RESOURCE_INIT,
  KINDS.RESOURCE_BEHAVIOR,
  KINDS.WORLD,
  KINDS.WORLD_BEHAVIOR,
  KINDS.PROCESSING_BEHAVIOR,
  KINDS.COMPOSER,
  KINDS.SUBWORKFLOW,
]);

// Roles offered in the New Function dialog. These are v2 workflow roles, not
// the old v1 execution stages. The chosen role becomes the function's folder
// (functions/<role>/) so placement is self-describing.
export const FUNCTION_ROLE_OPTIONS = [
  { kind: KINDS.AGENT_CREATE, label: 'Agent · creation (in World)' },
  { kind: KINDS.AGENT_BEHAVIOR, label: 'Agent · behavior' },
  { kind: KINDS.RESOURCE_INIT, label: 'Resource · initialization' },
  { kind: KINDS.RESOURCE_BEHAVIOR, label: 'Resource · behavior' },
  { kind: KINDS.WORLD, label: 'World · setup' },
  { kind: KINDS.WORLD_BEHAVIOR, label: 'World · behavior (per-step)' },
  { kind: KINDS.PROCESSING_BEHAVIOR, label: 'Reporting' },
];

// A contract declares what a behaviour reads/writes/owns — the I/O discipline.
// (There is no phase: iteration is decided by ownership/`for_each`, not a tag.)
export const defaultContractForKind = (kind, options = {}) => {
  const ownerKind = options.kindName;

  switch (kind) {
    case KINDS.AGENT_CREATE:
      // Collective creation: brings agents into existence (placement + wrap into
      // the population). Runs once, so it writes the whole agent collection.
      return {
        owner: { type: 'agent', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['world.self', 'resource.collection'],
        writes: ['agent.collection'],
        emits: [],
      };
    case KINDS.AGENT_BEHAVIOR:
      return {
        owner: { type: 'agent', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['agent.self'],
        writes: ['agent.self'],
        emits: [],
      };
    case KINDS.RESOURCE_INIT:
      return {
        owner: { type: 'resource', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['world.self'],
        writes: ['resource.self'],
        emits: [],
      };
    case KINDS.RESOURCE_BEHAVIOR:
      return {
        owner: { type: 'resource', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['resource.self'],
        writes: ['resource.self'],
        emits: [],
      };
    case KINDS.WORLD:
      return {
        owner: { type: 'world' },
        reads: [],
        writes: ['world.self'],
        emits: [],
      };
    case KINDS.WORLD_BEHAVIOR:
      return {
        owner: { type: 'world' },
        reads: ['agent.collection', 'resource.collection', 'world.self'],
        writes: ['world.self', 'resource.collection'],
        emits: [],
      };
    case KINDS.PROCESSING_BEHAVIOR:
      return {
        reads: ['agents', 'resources', 'world', 'simulation.results'],
        writes: [],
        emits: [],
      };
    default:
      return null;
  }
};

// Legacy registry category derived from a role/kind. This no longer drives
// execution (the workflow graph does); it only satisfies the historical
// @register_function enum while older registry consumers still expect it.
export const ROLE_TO_COMPATIBILITY_CATEGORY = {
  [KINDS.AGENT_CREATE]: 'INITIALIZATION',
  [KINDS.RESOURCE_INIT]: 'INITIALIZATION',
  [KINDS.WORLD]: 'INITIALIZATION',
  [KINDS.AGENT_BEHAVIOR]: 'INTRACELLULAR',
  [KINDS.RESOURCE_BEHAVIOR]: 'WORLD',
  [KINDS.WORLD_BEHAVIOR]: 'DIFFUSION',
  [KINDS.PROCESSING_BEHAVIOR]: 'FINALIZATION',
};

// Backward-compatible export for older imports. Prefer
// ROLE_TO_COMPATIBILITY_CATEGORY in new code.
export const KIND_TO_CATEGORY = ROLE_TO_COMPATIBILITY_CATEGORY;

export const variantForKind = (kind) => {
  switch (kind) {
    case KINDS.AGENT_BEHAVIOR:
      return 'cyan';
    case KINDS.RESOURCE_BEHAVIOR:
    case KINDS.RESOURCE_INIT:
      return 'orange';
    case KINDS.PROCESSING_BEHAVIOR:
    case KINDS.SUBWORKFLOW:
      return 'purple';
    case KINDS.COMPOSER:
      return 'orange';
    // Agent creation is authored in the World tab, so it wears the World color.
    case KINDS.AGENT_CREATE:
    case KINDS.WORLD:
    case KINDS.WORLD_BEHAVIOR:
      return 'green';
    case KINDS.SCHEDULER:
    case KINDS.INIT_SEQUENCE:
      return 'slate';
    default:
      return 'purple';
  }
};

// ---------------------------------------------------------------------------
// SINGLE SOURCE OF TRUTH: which navigable GUI tab OWNS (authors/edits) a canvas
// of each subworkflow kind. Every consumer derives from this one map — the
// call-node "go to canvas" link (SubWorkflowCallNode), the Overview deep links
// (overviewModel), the Parameters dashboard, and the Agents/World tab canvas
// lists (AgentsView/WorldView). Change where a kind is authored HERE, once; the
// whole GUI follows and cannot disagree with itself.
//
// Tabs are the buttons in MainTabSelector (Overview · Agents · Resources ·
// World · Initialization · Scheduler · Planner · Processing · Results). `null`
// = no owning entity tab (main/composer, generic subworkflows).
//
// IMPORTANT: agent CREATION is authored in World, not Agents. The Agents tab
// holds per-agent Steps only — every agent node runs per-agent.
export const KIND_TO_TAB = {
  [KINDS.AGENT_CREATE]: 'world',
  [KINDS.AGENT_BEHAVIOR]: 'agents',
  [KINDS.RESOURCE_INIT]: 'resources',
  [KINDS.RESOURCE_BEHAVIOR]: 'resources',
  [KINDS.WORLD]: 'world',
  [KINDS.WORLD_BEHAVIOR]: 'world',
  [KINDS.PROCESSING_BEHAVIOR]: 'processing',
  [KINDS.INIT_SEQUENCE]: 'initialization',
  [KINDS.SCHEDULER]: 'scheduler',
  [KINDS.COMPOSER]: null,
  [KINDS.SUBWORKFLOW]: null,
};

// User-facing entity family for a subworkflow kind. Used only for the
// human-readable "Load Behaviour" mismatch notice (Agent / Resource / World /
// Processing). The internal sub-kinds (create/init vs behavior) are unchanged —
// this is a label-only collapse. Kinds with no entity family (composer,
// subworkflow, scheduler, init_sequence) are intentionally absent → no notice.
export const KIND_TO_ENTITY = {
  [KINDS.AGENT_CREATE]: 'Agent',
  [KINDS.AGENT_BEHAVIOR]: 'Agent',
  [KINDS.RESOURCE_INIT]: 'Resource',
  [KINDS.RESOURCE_BEHAVIOR]: 'Resource',
  [KINDS.WORLD]: 'World',
  [KINDS.WORLD_BEHAVIOR]: 'World',
  [KINDS.PROCESSING_BEHAVIOR]: 'Processing',
  // Legacy alias: pre-migration exports tag agent creation as 'agent_init'
  // (now 'agent_create'). Same entity family — keep the load notice accurate
  // for those existing .subworkflow.json files.
  agent_init: 'Agent',
};
