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

// Roles offered in the New Function dialog — the subset of function-hosting
// kinds a biologist actually authors functions for. The chosen kind becomes the
// function's folder (functions/<kind>/) so placement is self-describing.
export const FUNCTION_ROLE_OPTIONS = [
  { kind: KINDS.AGENT_INIT, label: 'Agent · initialization' },
  { kind: KINDS.AGENT_BEHAVIOR, label: 'Agent · behaviour' },
  { kind: KINDS.RESOURCE_INIT, label: 'Resource · initialization' },
  { kind: KINDS.RESOURCE_BEHAVIOR, label: 'Resource · behaviour' },
  { kind: KINDS.ENV_INIT, label: 'Environment · initialization' },
  { kind: KINDS.ENV_BEHAVIOR, label: 'Environment · behaviour' },
  { kind: KINDS.PROCESSING_BEHAVIOR, label: 'Processing' },
];

// Engine execution category derived from a role/kind. The category no longer
// drives execution (the workflow graph does) — it only satisfies the
// @register_function enum and is never shown to the user.
export const KIND_TO_CATEGORY = {
  [KINDS.AGENT_INIT]: 'INITIALIZATION',
  [KINDS.RESOURCE_INIT]: 'INITIALIZATION',
  [KINDS.SPACE]: 'INITIALIZATION',
  [KINDS.ENV_INIT]: 'INITIALIZATION',
  [KINDS.AGENT_BEHAVIOR]: 'INTRACELLULAR',
  [KINDS.RESOURCE_BEHAVIOR]: 'ENVIRONMENT',
  [KINDS.ENV_BEHAVIOR]: 'DIFFUSION',
  [KINDS.PROCESSING_BEHAVIOR]: 'FINALIZATION',
};

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
