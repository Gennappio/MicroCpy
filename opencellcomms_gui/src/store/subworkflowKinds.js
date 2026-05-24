export const KINDS = {
  COMPOSER: 'composer',
  SUBWORKFLOW: 'subworkflow',
  AGENT_INIT: 'agent_init',
  AGENT_BEHAVIOR: 'agent_behavior',
  ENV_INIT: 'env_init',
  ENV_BEHAVIOR: 'env_behavior',
  PROCESSING_BEHAVIOR: 'processing_behavior',
  SCHEDULER: 'scheduler',
};

export const MAIN_TABS = {
  AGENTS: 'agents',
  ENVIRONMENT: 'environment',
  SCHEDULER: 'scheduler',
  PLANNER: 'planner',
  PROCESSING: 'processing',
  RESULTS: 'results',
};

export const SCHEDULER_NAME = '__scheduler__';

export const BEHAVIOR_KINDS = new Set([
  KINDS.AGENT_BEHAVIOR,
  KINDS.ENV_BEHAVIOR,
  KINDS.PROCESSING_BEHAVIOR,
]);

// All canvases where function nodes can be placed (everything except scheduler).
// Init canvases hold functions too (e.g. setup_population, setup_substances).
export const FUNCTION_HOSTING_KINDS = new Set([
  KINDS.AGENT_INIT,
  KINDS.AGENT_BEHAVIOR,
  KINDS.ENV_INIT,
  KINDS.ENV_BEHAVIOR,
  KINDS.PROCESSING_BEHAVIOR,
  KINDS.COMPOSER,
  KINDS.SUBWORKFLOW,
]);

export const variantForKind = (kind) => {
  switch (kind) {
    case KINDS.AGENT_BEHAVIOR:
    case KINDS.AGENT_INIT:
      return 'blue';
    case KINDS.ENV_BEHAVIOR:
    case KINDS.ENV_INIT:
      return 'green';
    case KINDS.PROCESSING_BEHAVIOR:
    case KINDS.SUBWORKFLOW:
      return 'purple';
    case KINDS.COMPOSER:
      return 'orange';
    case KINDS.SCHEDULER:
      return 'slate';
    default:
      return 'purple';
  }
};
