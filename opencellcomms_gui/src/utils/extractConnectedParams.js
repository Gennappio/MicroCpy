/**
 * extractConnectedParams - Shared utility for extracting connected parameter
 * nodes from workflow stage nodes and edges.
 *
 * Used by both ParametersDashboard (direct canvas editing) and PlannerView
 * (override-based editing).
 */

const PARAM_NODE_TYPES = new Set(['parameterNode', 'listParameterNode', 'dictParameterNode']);

/**
 * Extract all connected parameters grouped by kind > stage > function.
 *
 * @param {Object} stageNodes  - { stageName: Node[] }
 * @param {Object} stageEdges  - { stageName: Edge[] }
 * @param {Object} workflowMetadata - workflow.metadata (for subworkflow_kinds)
 * @returns {{ composer: Object, subworkflow: Object }}
 */
export function extractConnectedParams(stageNodes, stageEdges, workflowMetadata) {
  const result = { composer: {}, subworkflow: {} };

  for (const stageName of Object.keys(stageNodes)) {
    const nodes = stageNodes[stageName] || [];
    const edges = stageEdges[stageName] || [];

    const kind =
      workflowMetadata?.gui?.subworkflow_kinds?.[stageName] ||
      (stageName === 'main' ? 'composer' : 'subworkflow');

    const nodeById = {};
    for (const n of nodes) nodeById[n.id] = n;

    for (const edge of edges) {
      const sourceNode = nodeById[edge.source];
      const targetNode = nodeById[edge.target];
      if (!sourceNode || !targetNode) continue;
      if (!PARAM_NODE_TYPES.has(sourceNode.type)) continue;
      if (targetNode.type !== 'workflowFunction') continue;

      const targetHandle = edge.targetHandle || '';
      if (!targetHandle.startsWith('param-')) continue;

      const paramName = targetHandle.replace('param-', '');

      const entry = {
        stageName,
        functionNodeId: targetNode.id,
        functionLabel: targetNode.data?.label || targetNode.id,
        functionName: targetNode.data?.functionName || '',
        paramNodeId: sourceNode.id,
        paramNodeType: sourceNode.type,
        paramName,
        paramNodeData: sourceNode.data,
      };

      if (!result[kind]) result[kind] = {};
      if (!result[kind][stageName]) result[kind][stageName] = {};
      const funcKey = targetNode.id;
      if (!result[kind][stageName][funcKey]) {
        result[kind][stageName][funcKey] = {
          functionLabel: entry.functionLabel,
          functionName: entry.functionName,
          params: [],
        };
      }
      result[kind][stageName][funcKey].params.push(entry);
    }
  }

  return result;
}

/**
 * Deep-clone helper.
 * Uses JSON round-trip to strip non-serializable values (functions like onEdit).
 */
function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Snapshot all connected parameter node data.
 * Returns { paramNodeId: deepClone(node.data) } for every param node that has
 * at least one edge to a workflowFunction node.
 *
 * @param {Object} stageNodes
 * @param {Object} stageEdges
 * @param {Object} workflowMetadata
 * @returns {Object}
 */
export function snapshotAllParamNodeData(stageNodes, stageEdges, workflowMetadata) {
  const grouped = extractConnectedParams(stageNodes, stageEdges, workflowMetadata);
  const snapshot = {};

  for (const kind of Object.values(grouped)) {
    for (const stage of Object.values(kind)) {
      for (const func of Object.values(stage)) {
        for (const entry of func.params) {
          if (!snapshot[entry.paramNodeId]) {
            snapshot[entry.paramNodeId] = deepClone(entry.paramNodeData);
          }
        }
      }
    }
  }

  return snapshot;
}
