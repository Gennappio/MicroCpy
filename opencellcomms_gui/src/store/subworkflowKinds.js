export const KINDS = {
  COMPOSER: 'composer',
  SUBWORKFLOW: 'subworkflow',
  AGENT_INIT: 'agent_init',
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
  KINDS.AGENT_INIT,
  KINDS.RESOURCE_INIT,
  KINDS.WORLD,
]);

// All canvases where function nodes can be placed (everything except scheduler).
// Init canvases hold functions too (e.g. setup_population, setup_substances).
export const FUNCTION_HOSTING_KINDS = new Set([
  KINDS.AGENT_INIT,
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
  { kind: KINDS.AGENT_INIT, label: 'Agent · initialization' },
  { kind: KINDS.AGENT_BEHAVIOR, label: 'Agent · behavior' },
  { kind: KINDS.RESOURCE_INIT, label: 'Resource · initialization' },
  { kind: KINDS.RESOURCE_BEHAVIOR, label: 'Resource · behavior' },
  { kind: KINDS.WORLD_BEHAVIOR, label: 'World · behavior (per-step)' },
  { kind: KINDS.PROCESSING_BEHAVIOR, label: 'Reporting' },
];

// A contract declares what a behaviour reads/writes/owns — the I/O discipline.
// (There is no phase: iteration is decided by ownership/`for_each`, not a tag.)
export const defaultContractForKind = (kind, options = {}) => {
  const ownerKind = options.kindName;

  switch (kind) {
    case KINDS.AGENT_INIT:
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
  [KINDS.AGENT_INIT]: 'INITIALIZATION',
  [KINDS.RESOURCE_INIT]: 'INITIALIZATION',
  [KINDS.WORLD]: 'INITIALIZATION',
  [KINDS.AGENT_BEHAVIOR]: 'INTRACELLULAR',
  [KINDS.RESOURCE_BEHAVIOR]: 'ENVIRONMENT',
  [KINDS.WORLD_BEHAVIOR]: 'DIFFUSION',
  [KINDS.PROCESSING_BEHAVIOR]: 'FINALIZATION',
};

// Backward-compatible export for older imports. Prefer
// ROLE_TO_COMPATIBILITY_CATEGORY in new code.
export const KIND_TO_CATEGORY = ROLE_TO_COMPATIBILITY_CATEGORY;

export const variantForKind = (kind) => {
  switch (kind) {
    case KINDS.AGENT_BEHAVIOR:
    case KINDS.AGENT_INIT:
      return 'blue';
    case KINDS.RESOURCE_BEHAVIOR:
    case KINDS.RESOURCE_INIT:
      return 'green';
    case KINDS.PROCESSING_BEHAVIOR:
    case KINDS.SUBWORKFLOW:
      return 'purple';
    case KINDS.COMPOSER:
      return 'orange';
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
