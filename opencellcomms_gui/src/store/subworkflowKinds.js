export const KINDS = {
  COMPOSER: 'composer',
  SUBWORKFLOW: 'subworkflow',
  AGENT_INIT: 'agent_init',
  AGENT_BEHAVIOR: 'agent_behavior',
  RESOURCE_INIT: 'resource_init',
  RESOURCE_BEHAVIOR: 'resource_behavior',
  SPACE: 'space',
  ENV_INIT: 'env_init',
  ENV_BEHAVIOR: 'env_behavior',
  PROCESSING_BEHAVIOR: 'processing_behavior',
  SCHEDULER: 'scheduler',
  INIT_SEQUENCE: 'init_sequence',
};

export const MAIN_TABS = {
  OVERVIEW: 'overview',
  AGENTS: 'agents',
  ENVIRONMENT: 'environment',
  INITIALIZATION: 'initialization',
  SCHEDULER: 'scheduler',
  PLANNER: 'planner',
  PROCESSING: 'processing',
  RESULTS: 'results',
};

export const SCHEDULER_NAME = '__scheduler__';
export const INIT_SEQUENCE_NAME = '__init_sequence__';
export const SPACE_NAME = '__space__';

export const BEHAVIOR_KINDS = new Set([
  KINDS.AGENT_BEHAVIOR,
  KINDS.RESOURCE_BEHAVIOR,
  KINDS.ENV_BEHAVIOR,
  KINDS.PROCESSING_BEHAVIOR,
]);

// Kinds that represent an init canvas — used by the Initialization tab palette
// (only these are draggable into __init_sequence__) and by the Scheduler palette
// (which must explicitly EXCLUDE these).
export const INIT_KINDS = new Set([
  KINDS.AGENT_INIT,
  KINDS.RESOURCE_INIT,
  KINDS.SPACE,
  KINDS.ENV_INIT,
]);

// All canvases where function nodes can be placed (everything except scheduler).
// Init canvases hold functions too (e.g. setup_population, setup_substances).
export const FUNCTION_HOSTING_KINDS = new Set([
  KINDS.AGENT_INIT,
  KINDS.AGENT_BEHAVIOR,
  KINDS.RESOURCE_INIT,
  KINDS.RESOURCE_BEHAVIOR,
  KINDS.SPACE,
  KINDS.ENV_INIT,
  KINDS.ENV_BEHAVIOR,
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
  { kind: KINDS.ENV_INIT, label: 'Environment · initialization' },
  { kind: KINDS.ENV_BEHAVIOR, label: 'Coupling / reconciliation' },
  { kind: KINDS.PROCESSING_BEHAVIOR, label: 'Reporting' },
];

export const PROCESS_PHASES = {
  INITIALIZATION: 'initialization',
  AGENT_BEHAVIOR: 'agent_behavior',
  RESOURCE_BEHAVIOR: 'resource_behavior',
  SPACE_BEHAVIOR: 'space_behavior',
  COUPLING: 'coupling',
  RECONCILIATION: 'reconciliation',
  REPORTING: 'reporting',
};

export const PROCESS_PHASE_OPTIONS = [
  { phase: PROCESS_PHASES.COUPLING, label: 'Coupling' },
  { phase: PROCESS_PHASES.RECONCILIATION, label: 'Reconciliation' },
  { phase: PROCESS_PHASES.REPORTING, label: 'Reporting' },
];

export const PROCESS_PHASE_LABELS = {
  [PROCESS_PHASES.INITIALIZATION]: 'Initialization',
  [PROCESS_PHASES.AGENT_BEHAVIOR]: 'Agent behavior',
  [PROCESS_PHASES.RESOURCE_BEHAVIOR]: 'Resource behavior',
  [PROCESS_PHASES.SPACE_BEHAVIOR]: 'Space behavior',
  [PROCESS_PHASES.COUPLING]: 'Coupling',
  [PROCESS_PHASES.RECONCILIATION]: 'Reconciliation',
  [PROCESS_PHASES.REPORTING]: 'Reporting',
};

export const defaultContractForKind = (kind, options = {}) => {
  const ownerKind = options.kindName;

  switch (kind) {
    case KINDS.AGENT_INIT:
      return {
        phase: PROCESS_PHASES.INITIALIZATION,
        owner: { type: 'agent', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['space.self', 'resource.collection'],
        writes: ['agent.collection'],
        emits: [],
      };
    case KINDS.AGENT_BEHAVIOR:
      return {
        phase: PROCESS_PHASES.AGENT_BEHAVIOR,
        owner: { type: 'agent', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['agent.self'],
        writes: ['agent.self'],
        emits: [],
      };
    case KINDS.RESOURCE_INIT:
      return {
        phase: PROCESS_PHASES.INITIALIZATION,
        owner: { type: 'resource', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['space.self'],
        writes: ['resource.self'],
        emits: [],
      };
    case KINDS.RESOURCE_BEHAVIOR:
      return {
        phase: PROCESS_PHASES.RESOURCE_BEHAVIOR,
        owner: { type: 'resource', ...(ownerKind ? { kind: ownerKind } : {}) },
        reads: ['resource.self'],
        writes: ['resource.self'],
        emits: [],
      };
    case KINDS.SPACE:
      return {
        phase: PROCESS_PHASES.INITIALIZATION,
        owner: { type: 'space' },
        reads: [],
        writes: ['space.self'],
        emits: [],
      };
    case KINDS.ENV_INIT:
      return {
        phase: PROCESS_PHASES.INITIALIZATION,
        owner: { type: 'environment' },
        reads: ['simulation.parameters'],
        writes: ['simulation.config', 'space.self', 'agent.collection', 'resource.collection'],
        emits: [],
      };
    case KINDS.ENV_BEHAVIOR:
      return defaultContractForProcessPhase(options.phase || PROCESS_PHASES.COUPLING);
    case KINDS.PROCESSING_BEHAVIOR:
      return {
        phase: PROCESS_PHASES.REPORTING,
        reads: ['agents', 'resources', 'space', 'simulation.results'],
        writes: [],
        emits: [],
      };
    default:
      return null;
  }
};

export const defaultContractForProcessPhase = (phase) => {
  switch (phase) {
    case PROCESS_PHASES.COUPLING:
      return {
        phase: PROCESS_PHASES.COUPLING,
        participants: [{ type: 'agent' }, { type: 'resource' }],
        reads: ['agent.collection', 'resource.collection', 'space.self'],
        writes: [],
        emits: [],
      };
    case PROCESS_PHASES.RECONCILIATION:
      return {
        phase: PROCESS_PHASES.RECONCILIATION,
        reads: ['intent.*', 'agent.collection', 'resource.collection', 'space.self'],
        writes: ['agent.collection', 'resource.self', 'space.self'],
        consumes: ['intent.*'],
        emits: [],
      };
    case PROCESS_PHASES.REPORTING:
      return {
        phase: PROCESS_PHASES.REPORTING,
        reads: ['agents', 'resources', 'space', 'simulation.results'],
        writes: [],
        emits: [],
      };
    default:
      return defaultContractForKind(KINDS.ENV_BEHAVIOR, { phase: PROCESS_PHASES.COUPLING });
  }
};

// Legacy registry category derived from a role/kind. This no longer drives
// execution (the workflow graph does); it only satisfies the historical
// @register_function enum while older registry consumers still expect it.
export const ROLE_TO_COMPATIBILITY_CATEGORY = {
  [KINDS.AGENT_INIT]: 'INITIALIZATION',
  [KINDS.RESOURCE_INIT]: 'INITIALIZATION',
  [KINDS.SPACE]: 'INITIALIZATION',
  [KINDS.ENV_INIT]: 'INITIALIZATION',
  [KINDS.AGENT_BEHAVIOR]: 'INTRACELLULAR',
  [KINDS.RESOURCE_BEHAVIOR]: 'ENVIRONMENT',
  [KINDS.ENV_BEHAVIOR]: 'DIFFUSION',
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
    case KINDS.ENV_BEHAVIOR:
    case KINDS.ENV_INIT:
    case KINDS.RESOURCE_BEHAVIOR:
    case KINDS.RESOURCE_INIT:
      return 'green';
    case KINDS.PROCESSING_BEHAVIOR:
    case KINDS.SUBWORKFLOW:
      return 'purple';
    case KINDS.COMPOSER:
      return 'orange';
    case KINDS.SPACE:
      return 'green';
    case KINDS.SCHEDULER:
    case KINDS.INIT_SEQUENCE:
      return 'slate';
    default:
      return 'purple';
  }
};
