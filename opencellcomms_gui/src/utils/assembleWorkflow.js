/**
 * Single source of truth for turning the LIVE canvas state (stageNodes /
 * stageEdges) into the workflow `subworkflows` map — including the synthesized
 * `main` composer.
 *
 * Used by BOTH `exportWorkflow` (what gets saved and run) and the read-only
 * Overview canvas (what you see assembled), so the two cannot diverge. The
 * stored `workflow.subworkflows` is only a cache refreshed at load/export; the
 * canvas graph is authoritative, so everything here reads from the canvas.
 */

import { INIT_SEQUENCE_NAME, controllerLabel } from '../store/subworkflowKinds';

export const deriveForEachForBehavior = (gui, behaviorName) => {
  // Iteration is OWNERSHIP-driven (scope = tab): a behaviour homed to an
  // agent/resource kind runs once per entity via the per-entity `for_each` ask;
  // everything else runs once per step. A behaviour that must run once must
  // therefore simply NOT be homed to an agent/resource kind (it lives on the
  // World/Scheduler side). There is no phase concept.
  const agentKind = (gui.agent_kinds || []).find((k) =>
    (k.behavior_subworkflows || []).includes(behaviorName),
  );
  if (agentKind) return { type: 'agent', kind: agentKind.name, order: 'random' };

  const resourceKind = (gui.resource_kinds || []).find((k) =>
    (k.behavior_subworkflows || []).includes(behaviorName),
  );
  if (resourceKind) return { type: 'resource', kind: resourceKind.name };

  return null;
};

/** Function/subworkflow-call node IDs reachable from the controller via
 *  func-out / init-out edges, in BFS order. The canvas graph — not the stored
 *  execution_order cache — is the source of truth for ordering. */
export const findReachableNodes = (nodes, edges, subworkflowName) => {
  const controllerNode =
    nodes.find((n) => n.type === 'initNode') ||
    nodes.find((n) => n.id === `controller-${subworkflowName}`);
  if (!controllerNode) return [];

  const adjacency = {};
  edges.forEach((edge) => {
    if (edge.sourceHandle === 'func-out' || edge.sourceHandle === 'init-out') {
      if (!adjacency[edge.source]) adjacency[edge.source] = [];
      adjacency[edge.source].push(edge.target);
    }
  });

  const visited = new Set([controllerNode.id]);
  const order = [];
  const queue = [controllerNode.id];
  while (queue.length > 0) {
    const current = queue.shift();
    for (const neighbor of adjacency[current] || []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      const node = nodes.find((n) => n.id === neighbor);
      if (node && (node.type === 'workflowFunction' || node.type === 'subworkflowCall')) {
        order.push(neighbor);
      }
      queue.push(neighbor);
    }
  }
  return order;
};

const parameterConnections = (edges, nodeId) =>
  edges
    .filter(
      (e) =>
        e.target === nodeId &&
        (e.targetHandle?.startsWith('params') || e.targetHandle?.startsWith('param-')),
    )
    .map((e) => e.source);

/** Rebuild one subworkflow's JSON from its live canvas nodes/edges. */
const rebuildSubworkflow = (workflow, name, nodes, edges) => {
  const cached = workflow.subworkflows[name] || {};
  const execution_order = findReachableNodes(nodes, edges, name);

  const functions = nodes
    .filter((n) => n.type === 'workflowFunction')
    .map((node) => ({
      id: node.id,
      function_name: node.data.functionName,
      function_file: node.data.functionFile || '',
      parameters: node.data.parameters || {},
      enabled: node.data.enabled !== false,
      position: node.position,
      description: node.data.description || '',
      custom_name: node.data.customName || '',
      step_count: node.data.stepCount || 1,
      parameter_nodes: parameterConnections(edges, node.id),
      ...(node.data.contract ? { contract: node.data.contract } : {}),
    }));

  const subworkflow_calls = nodes
    .filter((n) => n.type === 'subworkflowCall')
    .map((node) => {
      const call = {
        id: node.id,
        type: 'subworkflow_call',
        subworkflow_name: node.data.subworkflowName,
        iterations: node.data.iterations || 1,
        parameters: node.data.parameters || {},
        enabled: node.data.enabled !== false,
        position: node.position,
        description: node.data.description || '',
        parameter_nodes: parameterConnections(edges, node.id),
      };
      const forEach =
        node.data.forEach ||
        deriveForEachForBehavior(workflow.metadata?.gui || {}, node.data.subworkflowName);
      if (forEach) call.for_each = forEach;
      if (node.data.results && node.data.results.trim() !== '') call.results = node.data.results;
      return call;
    });

  const parameters = [
    ...nodes
      .filter((n) => n.type === 'parameterNode')
      .map((node) => ({
        id: node.id,
        label: node.data.label || 'Parameters',
        parameters: node.data.parameters || {},
        position: node.position,
      })),
    ...nodes
      .filter((n) => n.type === 'listParameterNode')
      .map((node) => ({
        id: node.id,
        type: 'listParameterNode',
        label: node.data.label || 'List',
        listType: node.data.listType || 'string',
        items: node.data.items || [],
        target_param: node.data.targetParam || 'items',
        position: node.position,
      })),
    ...nodes
      .filter((n) => n.type === 'dictParameterNode')
      .map((node) => ({
        id: node.id,
        type: 'dictParameterNode',
        label: node.data.label || 'Dictionary',
        entries: node.data.entries || [],
        target_param: node.data.targetParam,
        position: node.position,
      })),
  ];

  const controllerNode =
    nodes.find((n) => n.type === 'initNode') ||
    nodes.find((n) => n.id === `controller-${name}`);
  const stepsParamNodeIds = controllerNode
    ? edges
        .filter((e) => e.target === controllerNode.id && e.targetHandle === 'steps-param')
        .map((e) => e.source)
    : [];
  let resolvedSteps = controllerNode?.data?.numberOfSteps || 1;
  if (stepsParamNodeIds.length > 0) {
    const pNode = nodes.find((n) => n.id === stepsParamNodeIds[0]);
    const v =
      pNode?.data?.parameters?.steps ??
      pNode?.data?.parameters?.step_count ??
      pNode?.data?.parameters?.numberOfSteps;
    if (v !== undefined && v !== '' && Number.isFinite(Number(v))) resolvedSteps = Number(v);
  }
  // Fall back to the persisted controller when this canvas was never mounted.
  const persisted = cached.controller;
  const controller = controllerNode
    ? {
        id: controllerNode.id,
        type: 'controller',
        label: controllerLabel(name),
        position: controllerNode.position,
        number_of_steps: resolvedSteps,
        ...(stepsParamNodeIds.length > 0 ? { parameter_nodes: stepsParamNodeIds } : {}),
      }
    : persisted
      ? {
          id: persisted.id || `controller-${name}`,
          type: 'controller',
          label: controllerLabel(name),
          position: persisted.position || { x: 100, y: 100 },
          number_of_steps: persisted.number_of_steps || 1,
        }
      : null;

  return {
    description: cached.description || '',
    enabled: cached.enabled !== false,
    deletable: cached.deletable !== false,
    ...(cached.contract ? { contract: cached.contract } : {}),
    controller,
    functions,
    subworkflow_calls,
    parameters,
    execution_order,
    input_parameters: cached.input_parameters || [],
  };
};

/** Synthesize the `main` composer from ABM structure (mutates `subworkflows`). */
const synthesizeMain = (workflow, subworkflows) => {
  const gui = workflow.metadata?.gui || {};
  const agentKinds = gui.agent_kinds || [];
  const resourceKinds = gui.resource_kinds || [];
  const worldMeta = gui.world || {};
  const processingMeta = gui.processing || {};
  const schedulerName = gui.scheduler?.subworkflow || '__scheduler__';
  const initSeqName = gui.init_sequence?.subworkflow || INIT_SEQUENCE_NAME;

  const hasAbmContent =
    agentKinds.length > 0 ||
    resourceKinds.length > 0 ||
    worldMeta.subworkflow ||
    (worldMeta.behavior_subworkflows || []).length > 0 ||
    (processingMeta.behavior_subworkflows || []).length > 0 ||
    !!subworkflows[schedulerName];
  if (!hasAbmContent) return;

  let callY = 200;
  const makeMainCall = (name, description, iterations = 1) => {
    const call = {
      id: `main-call-${name}`,
      type: 'subworkflow_call',
      subworkflow_name: name,
      iterations,
      parameters: {},
      enabled: true,
      position: { x: 400, y: callY },
      description,
      parameter_nodes: [],
    };
    callY += 120;
    return call;
  };

  const mainCalls = [];
  if (subworkflows[initSeqName]) mainCalls.push(makeMainCall(initSeqName, 'Initialization sequence'));
  if (subworkflows[schedulerName]) {
    const loopSteps = subworkflows[schedulerName]?.controller?.number_of_steps || 1;
    mainCalls.push(makeMainCall(schedulerName, 'Main simulation loop', loopSteps));
  }
  (processingMeta.behavior_subworkflows || []).forEach((b) =>
    mainCalls.push(makeMainCall(b, `Processing: ${b}`)),
  );

  subworkflows.main = {
    description: 'Synthesized main workflow (do not edit — managed by ABM structure)',
    enabled: true,
    deletable: false,
    controller: {
      id: 'controller-main',
      type: 'controller',
      label: controllerLabel('main'),
      position: { x: 100, y: 100 },
      number_of_steps: 1,
    },
    functions: [],
    subworkflow_calls: mainCalls,
    parameters: [],
    execution_order: mainCalls.map((c) => c.id),
    input_parameters: [],
  };
};

/** Rebuild the full `subworkflows` map (incl. synthesized `main`) from live canvases. */
export const assembleSubworkflowsFromStages = (workflow, stageNodes, stageEdges) => {
  const subworkflows = {};
  Object.keys(workflow.subworkflows || {}).forEach((name) => {
    const nodes = stageNodes[name];
    // Never materialized on a canvas this session → trust the loaded cache.
    if (!nodes) {
      subworkflows[name] = workflow.subworkflows[name];
      return;
    }
    subworkflows[name] = rebuildSubworkflow(workflow, name, nodes, stageEdges[name] || []);
  });
  synthesizeMain(workflow, subworkflows);
  return subworkflows;
};

/** A workflow object whose `subworkflows` reflect the live canvases. */
export const assembleLiveWorkflow = (workflow, stageNodes, stageEdges) => ({
  ...workflow,
  subworkflows: assembleSubworkflowsFromStages(workflow, stageNodes, stageEdges),
});
