/**
 * Build the read-only Overview graph (React Flow nodes + edges) by DERIVING it
 * from the assembled workflow — never hand-authored, so it cannot drift from
 * what actually runs.
 *
 * Source of truth, in order:
 *   main.execution_order
 *     → __init_sequence__  (init behaviours, once)
 *     → __scheduler__      (per-tick loop, ×iterations)
 *     → processing         (reporting, once)
 *
 * Inside the loop, any behaviour that contains the engine `apply_reconciliation`
 * function is expanded into the canonical, locked reconciliation pipeline
 * (see reconciliationSteps.js). Those are "system" nodes: visible, ordered,
 * read-only.
 */

import { computeSubworkflowKinds } from '../store/computeSubworkflowKinds';
import { variantForKind } from '../store/subworkflowKinds';
import {
  RECONCILIATION_STEPS,
  RECONCILIATION_FUNCTION,
  RECONCILIATION_SOURCE,
} from './reconciliationSteps';

// Which authoring tab owns a given subworkflow kind (mirrors the deep-link map
// already used by SubWorkflowCallNode).
const KIND_TO_TAB = {
  agent_init: 'agents',
  agent_behavior: 'agents',
  resource_init: 'resources',
  resource_behavior: 'resources',
  space: 'space',
  env_init: 'environment',
  env_behavior: 'environment',
  processing_behavior: 'processing',
  scheduler: 'scheduler',
  init_sequence: 'initialization',
};

const COL_X = 240;       // main spine
const STEP_X = 320;      // indented reconciliation steps
const Y_HEADER = 96;     // gap consumed by a phase header
const Y_NODE = 132;      // gap consumed by a behaviour node
const Y_STEP = 92;       // gap consumed by a locked system step

/** Resolve a subworkflow's ordered subworkflow_calls (execution_order first). */
const orderedCalls = (sw) => {
  if (!sw) return [];
  const calls = sw.subworkflow_calls || [];
  const byId = Object.fromEntries(calls.map((c) => [c.id, c]));
  const order = sw.execution_order && sw.execution_order.length
    ? sw.execution_order
    : calls.map((c) => c.id);
  return order.map((id) => byId[id]).filter(Boolean);
};

const forEachLabel = (forEach) => {
  if (!forEach?.kind) return null;
  if (forEach.type === 'resource') return `for each ${forEach.kind}`;
  const order = forEach.order ? ` (${forEach.order})` : '';
  return `for each ${forEach.kind}${order}`;
};

/**
 * @returns {{ nodes: Array, edges: Array, empty: boolean, reason?: string,
 *            loopCount: number }}
 */
export const buildOverviewModel = (workflow) => {
  const gui = workflow?.metadata?.gui;
  const subs = workflow?.subworkflows || {};
  if (!gui || !subs.main) {
    return {
      nodes: [],
      edges: [],
      empty: true,
      reason: 'Overview needs an assembled ABM workflow (a synthesized main).',
      loopCount: 0,
    };
  }

  const kinds = gui.subworkflow_kinds || computeSubworkflowKinds(workflow);

  const nodes = [];
  const edges = [];
  let y = 24;
  let prevId = null;

  const connect = (toId, opts = {}) => {
    if (prevId) {
      edges.push({
        id: `e-${prevId}-${toId}`,
        source: prevId,
        target: toId,
        type: 'smoothstep',
        ...opts,
      });
    }
    prevId = toId;
  };

  const pushHeader = (id, label, sublabel, tone) => {
    nodes.push({
      id,
      type: 'overviewHeader',
      position: { x: COL_X - 8, y },
      data: { label, sublabel, tone },
      draggable: false,
      selectable: false,
    });
    connect(id);
    y += Y_HEADER;
  };

  // Emit one collapsed authored-behaviour node for a subworkflow_call.
  const pushBehavior = (idPrefix, call) => {
    const name = call.subworkflow_name;
    const sw = subs[name];
    const kind = kinds[name];
    const id = `${idPrefix}:${call.id}`;
    nodes.push({
      id,
      type: 'overviewNode',
      position: { x: COL_X, y },
      data: {
        title: name,
        variant: variantForKind(kind),
        forEach: forEachLabel(call.for_each),
        iterations: call.iterations > 1 ? call.iterations : null,
        description: sw?.description || call.description || '',
        navTab: KIND_TO_TAB[kind] || null,
        navTarget: name,
      },
      draggable: false,
    });
    connect(id);
    y += Y_NODE;
    return { id, sw };
  };

  // If a behaviour runs the engine reconciliation, expand the locked pipeline.
  const expandReconciliation = (sw) => {
    const fn = (sw?.functions || []).find(
      (f) => f.function_name === RECONCILIATION_FUNCTION,
    );
    if (!fn) return;
    const cullDead = fn.parameters?.cull_dead ?? true;

    pushHeader(
      'recon:header',
      'apply_reconciliation',
      `${RECONCILIATION_SOURCE} · locked`,
      'system',
    );

    RECONCILIATION_STEPS.forEach((step) => {
      const id = `recon:${step.id}`;
      const knob =
        step.param === 'cull_dead'
          ? { knob: `cull_dead = ${cullDead}` }
          : {};
      nodes.push({
        id,
        type: 'overviewNode',
        position: { x: STEP_X, y },
        data: {
          title: step.label,
          variant: 'slate',
          system: true,
          intent: step.intent,
          description: step.description,
          source: RECONCILIATION_SOURCE,
          ...knob,
        },
        draggable: false,
        selectable: false,
      });
      connect(id, { style: { stroke: '#94a3b8', strokeDasharray: '4 3' } });
      y += Y_STEP;
    });
  };

  // ── INITIALIZATION ────────────────────────────────────────────────────────
  const initSeqName = gui.init_sequence?.subworkflow;
  const schedulerName = gui.scheduler?.subworkflow;
  const mainCalls = orderedCalls(subs.main);

  const initCalls = orderedCalls(subs[initSeqName]);
  if (initCalls.length) {
    pushHeader('hdr:init', 'Initialization', 'runs once at t = 0', 'init');
    initCalls.forEach((call) => pushBehavior('init', call));
  }

  // ── MAIN LOOP ─────────────────────────────────────────────────────────────
  const schedulerCall = mainCalls.find((c) => c.subworkflow_name === schedulerName);
  const loopCount =
    schedulerCall?.iterations ||
    subs[schedulerName]?.controller?.number_of_steps ||
    1;
  const loopCalls = orderedCalls(subs[schedulerName]);

  let firstLoopId = null;
  let lastLoopId = null;
  if (loopCalls.length) {
    pushHeader(
      'hdr:loop',
      'Main loop',
      `the scheduler owns iteration · ×${loopCount} ticks`,
      'loop',
    );
    loopCalls.forEach((call) => {
      const { id, sw } = pushBehavior('loop', call);
      if (!firstLoopId) firstLoopId = id;
      lastLoopId = id;
      expandReconciliation(sw);
      lastLoopId = prevId; // include any expanded system steps in the loop band
    });

    // Dashed return edge expresses "repeat next tick" without group-node math.
    if (firstLoopId && lastLoopId && firstLoopId !== lastLoopId) {
      edges.push({
        id: 'e-loop-back',
        source: lastLoopId,
        target: firstLoopId,
        type: 'smoothstep',
        animated: true,
        label: 'next tick',
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 4,
        labelBgStyle: { fill: '#eef2ff', color: '#4338ca' },
        style: { stroke: '#6366f1', strokeDasharray: '6 4' },
      });
    }
  }

  // ── PROCESSING ────────────────────────────────────────────────────────────
  const processingCalls = mainCalls.filter(
    (c) =>
      c.subworkflow_name !== initSeqName && c.subworkflow_name !== schedulerName,
  );
  if (processingCalls.length) {
    pushHeader('hdr:proc', 'Processing', 'runs once at the end', 'processing');
    processingCalls.forEach((call) => pushBehavior('proc', call));
  }

  return { nodes, edges, empty: nodes.length === 0, loopCount };
};
