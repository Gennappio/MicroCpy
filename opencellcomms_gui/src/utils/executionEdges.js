/**
 * Canonical execution-flow edge helpers for orchestrator / behaviour canvases.
 *
 * A subworkflow's run order is carried by the canvas graph: `assembleWorkflow.js`
 * `findReachableNodes` rebuilds `execution_order` by BFS over edges whose
 * `sourceHandle` is `func-out` (or `init-out`), and only edge-reachable call nodes
 * make it into the exported `execution_order`. An order-carrying edge MUST use this
 * exact shape (`func-out` -> `func-in`) or it is invisible to the exporter and its
 * target call is silently dropped from `execution_order` at runtime.
 *
 * This is the single source of that edge shape; it matches the load-path edges built
 * in `workflowIOSlice.js`.
 */

/**
 * True for an execution-flow edge — one that `findReachableNodes` traverses — as
 * opposed to a parameter edge (parameterNode -> a call's `params-*` handle). Use this
 * when picking chain neighbours so a parameter edge is never mistaken for an
 * execution edge (which would stitch a bogus edge into the run order).
 */
export const isExecEdge = (edge) =>
  edge.sourceHandle === 'func-out' || edge.sourceHandle === 'init-out';

export const execEdge = (sourceId, targetId) => ({
  id: `e-${sourceId}-${targetId}`,
  source: sourceId,
  sourceHandle: 'func-out',
  target: targetId,
  targetHandle: 'func-in',
  type: 'default',
  animated: true,
  markerEnd: { type: 'arrowclosed', width: 10, height: 10 },
  style: { strokeWidth: 6 },
});

/**
 * Build the `controller -> first -> ... -> last` execution-flow chain for an ordered
 * list of node ids. Returns [] when there are no nodes.
 */
export const wireChain = (controllerId, orderedNodeIds) => {
  const ids = orderedNodeIds || [];
  if (ids.length === 0) return [];
  const edges = [execEdge(controllerId, ids[0])];
  for (let i = 0; i < ids.length - 1; i += 1) {
    edges.push(execEdge(ids[i], ids[i + 1]));
  }
  return edges;
};
