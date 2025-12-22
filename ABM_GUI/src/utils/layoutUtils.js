/**
 * Layout utilities using dagre for automatic node positioning
 */
import dagre from '@dagrejs/dagre';

// Node dimensions for layout calculations
const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;
const PARAM_NODE_WIDTH = 180;
const PARAM_NODE_HEIGHT = 60;

/**
 * Apply dagre layout to nodes and edges
 * Creates a staggered left-to-right layout where:
 * - Parameter nodes are positioned to the left of their connected function nodes
 * - Function nodes flow left-to-right based on execution order
 * 
 * @param {Array} nodes - React Flow nodes
 * @param {Array} edges - React Flow edges
 * @param {Object} options - Layout options
 * @returns {Array} - Nodes with updated positions
 */
export function getLayoutedNodes(nodes, edges, options = {}) {
  const {
    direction = 'LR', // Left to Right
    nodeSpacing = 80,
    rankSpacing = 150,
  } = options;

  // Create a new dagre graph
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  // Configure the graph layout
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: nodeSpacing,
    ranksep: rankSpacing,
    marginx: 50,
    marginy: 50,
  });

  // Add nodes to the graph
  nodes.forEach((node) => {
    const isParamNode = node.type === 'parameterNode';
    dagreGraph.setNode(node.id, {
      width: isParamNode ? PARAM_NODE_WIDTH : NODE_WIDTH,
      height: isParamNode ? PARAM_NODE_HEIGHT : NODE_HEIGHT,
    });
  });

  // Add edges to the graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Run the layout algorithm
  dagre.layout(dagreGraph);

  // Apply the calculated positions to nodes
  return nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const isParamNode = node.type === 'parameterNode';
    const width = isParamNode ? PARAM_NODE_WIDTH : NODE_WIDTH;
    const height = isParamNode ? PARAM_NODE_HEIGHT : NODE_HEIGHT;

    return {
      ...node,
      position: {
        // Dagre gives center position, convert to top-left for React Flow
        x: nodeWithPosition.x - width / 2,
        y: nodeWithPosition.y - height / 2,
      },
    };
  });
}

/**
 * Create a staggered layout specifically for workflow stages
 * This creates a vertically flowing layout where:
 * - Function nodes are arranged vertically with staggered horizontal offsets
 * - Parameter nodes are positioned to the left of their connected functions
 * - Nodes are spaced out to avoid overlaps
 *
 * @param {Array} functionNodes - Function nodes
 * @param {Array} paramNodes - Parameter nodes
 * @param {Array} edges - All edges
 * @param {Array} executionOrder - Order of function execution
 * @returns {Object} - { nodes: layoutedNodes, edges: edges }
 */
export function createStaggeredLayout(functionNodes, paramNodes, edges, executionOrder = []) {
  // Layout constants for vertical staggered layout
  const LEFT_X = 100;
  const RIGHT_X = 800;
  const PARAM_OFFSET_X = -350; // Parameter nodes to the left of function
  const START_Y = 50;
  const VERTICAL_SPACING = 270; // Space between each pair vertically

  // Build a map of function order
  const orderMap = {};
  executionOrder.forEach((funcId, idx) => {
    orderMap[funcId] = idx;
  });

  // Assign order to functions not in execution order
  let nextIdx = executionOrder.length;
  functionNodes.forEach((node) => {
    if (!(node.id in orderMap)) {
      orderMap[node.id] = nextIdx++;
    }
  });

  // Position function nodes in a vertical staggered pattern
  // Each pair (function + params) goes down, alternating left/right
  const layoutedFuncNodes = functionNodes.map((node) => {
    const orderIdx = orderMap[node.id] || 0;
    // Alternate between left and right for each node
    const isLeft = orderIdx % 2 === 0;
    const yPos = START_Y + (orderIdx * VERTICAL_SPACING);

    return {
      ...node,
      position: {
        x: isLeft ? LEFT_X : RIGHT_X,
        y: yPos,
      },
    };
  });

  // Build a map of function positions for parameter node placement
  const funcPositionMap = {};
  layoutedFuncNodes.forEach((node) => {
    funcPositionMap[node.id] = node.position;
  });

  // Position parameter nodes based on their connected function
  // Parameters stay with their function (same column, same row)
  const layoutedParamNodes = paramNodes.map((paramNode) => {
    // Find the function this parameter is connected to
    const connectedEdge = edges.find(
      (e) => e.source === paramNode.id && e.sourceHandle === 'params'
    );

    if (connectedEdge && funcPositionMap[connectedEdge.target]) {
      const funcPos = funcPositionMap[connectedEdge.target];
      // Position parameter node to the left of its function
      return {
        ...paramNode,
        position: {
          x: funcPos.x + PARAM_OFFSET_X,
          y: funcPos.y, // Same Y as function
        },
      };
    }

    // Fallback position if no connection found
    return paramNode;
  });

  return {
    nodes: [...layoutedParamNodes, ...layoutedFuncNodes],
    edges,
  };
}

export default { getLayoutedNodes, createStaggeredLayout };

