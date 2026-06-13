/**
 * Derive the `subworkflow_kinds` map from a workflow's ABM metadata.
 *
 * Phase 14B: `subworkflow_kinds` is no longer persisted to JSON. It is computed
 * at load time and after each ABM mutation, then stored in
 * `workflow.metadata.gui.subworkflow_kinds` as a runtime cache so existing
 * components (which read that field) keep working without changes.
 *
 * Derivation table (in priority order — later wins on collision, which
 * should not happen in a valid workflow):
 *   - main                                        → composer
 *   - scheduler.subworkflow                       → scheduler
 *   - init_sequence.subworkflow                   → init_sequence
 *   - environment.init_subworkflow                → env_init
 *   - environment.behavior_subworkflows[i]        → env_behavior
 *   - agent_kinds[i].init_subworkflow             → agent_init
 *   - agent_kinds[i].behavior_subworkflows[j]     → agent_behavior
 *   - processing.behavior_subworkflows[i]         → processing_behavior
 */

import { KINDS } from './subworkflowKinds';

export const computeSubworkflowKinds = (workflow) => {
  const gui = workflow?.metadata?.gui || {};
  const subworkflows = workflow?.subworkflows || {};
  const kinds = {};

  const agentKinds = gui.agent_kinds || [];
  const resourceKinds = gui.resource_kinds || [];
  const env = gui.environment || {};
  const scheduler = gui.scheduler || {};
  const processing = gui.processing || {};
  const initSeq = gui.init_sequence || {};

  if (scheduler.subworkflow) kinds[scheduler.subworkflow] = KINDS.SCHEDULER;
  if (initSeq.subworkflow) kinds[initSeq.subworkflow] = 'init_sequence';

  const space = gui.space || {};
  if (space.subworkflow) kinds[space.subworkflow] = KINDS.SPACE;

  if (env.init_subworkflow) kinds[env.init_subworkflow] = KINDS.ENV_INIT;
  (env.behavior_subworkflows || []).forEach((n) => {
    kinds[n] = KINDS.ENV_BEHAVIOR;
  });

  agentKinds.forEach((k) => {
    if (k.init_subworkflow) kinds[k.init_subworkflow] = KINDS.AGENT_INIT;
    (k.behavior_subworkflows || []).forEach((b) => {
      kinds[b] = KINDS.AGENT_BEHAVIOR;
    });
  });

  resourceKinds.forEach((k) => {
    if (k.init_subworkflow) kinds[k.init_subworkflow] = KINDS.RESOURCE_INIT;
    (k.behavior_subworkflows || []).forEach((b) => {
      kinds[b] = KINDS.RESOURCE_BEHAVIOR;
    });
  });

  (processing.behavior_subworkflows || []).forEach((n) => {
    kinds[n] = KINDS.PROCESSING_BEHAVIOR;
  });

  if (subworkflows.main) kinds.main = KINDS.COMPOSER;

  // Composable workflows: any subworkflow reachable from main's subworkflow_calls
  // (directly or transitively) that has no ABM-derived kind is treated as a
  // generic composer child. This lets a bare `main → child composers` workflow
  // (or a pure processing canvas) load and render without the full
  // agent/environment ABM scaffolding.
  const visit = (name) => {
    const sw = subworkflows[name];
    if (!sw) return;
    (sw.subworkflow_calls || []).forEach((call) => {
      const target = call.subworkflow_name;
      if (!target || !(target in subworkflows) || target in kinds) return;
      kinds[target] = KINDS.SUBWORKFLOW;
      visit(target);
    });
  };
  if (subworkflows.main) visit('main');

  return kinds;
};

/** Return names of subworkflows present in `workflow.subworkflows` but not
 *  reachable from any ABM metadata field (and not `main`). */
export const findOrphanSubworkflows = (workflow) => {
  const kinds = computeSubworkflowKinds(workflow);
  const subworkflows = workflow?.subworkflows || {};
  return Object.keys(subworkflows).filter((name) => !(name in kinds));
};

/** Return a list of missing required ABM metadata fields (empty if all present). */
export const validateAbmMetadata = (workflowJson) => {
  const gui = workflowJson?.metadata?.gui;
  if (!gui) return ['metadata.gui'];
  const missing = [];
  if (!Array.isArray(gui.agent_kinds)) missing.push('agent_kinds');
  if (!gui.environment || typeof gui.environment !== 'object') missing.push('environment');
  if (!gui.scheduler || typeof gui.scheduler !== 'object') missing.push('scheduler');
  if (!gui.processing || typeof gui.processing !== 'object') missing.push('processing');
  return missing;
};

/** Return a new workflow object with `metadata.gui.subworkflow_kinds` recomputed. */
export const withDerivedKinds = (workflow) => {
  const kinds = computeSubworkflowKinds(workflow);
  return {
    ...workflow,
    metadata: {
      ...workflow.metadata,
      gui: {
        ...(workflow.metadata?.gui || {}),
        subworkflow_kinds: kinds,
      },
    },
  };
};
