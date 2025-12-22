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
 * - Each function and its parameters are grouped in a visual container
 * - Groups are arranged vertically with staggered horizontal offsets
 * - Parameter nodes are displayed individually within the group
 *
 * @param {Array} functionNodes - Function nodes
 * @param {Array} paramNodes - Parameter nodes
 * @param {Array} edges - All edges
 * @param {Array} executionOrder - Order of function execution
 * @returns {Object} - { nodes: layoutedNodes, edges: edges }
 */
export function createStaggeredLayout(functionNodes, paramNodes, edges, executionOrder = []) {
  // Layout constants
  const LEFT_X = 50;
  const RIGHT_X = 1300; // MUCH LARGER - increased to accommodate very wide groups
  const START_Y = 50;
  const GROUP_PADDING = 40; // Increased padding for more space
  const PARAM_NODE_HEIGHT = 50;
  const FUNC_NODE_HEIGHT = 100;
  const PARAM_SPACING = 10;

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

  // Build a map of which parameters connect to which function
  const funcToParams = {};
  functionNodes.forEach((func) => {
    funcToParams[func.id] = [];
  });
  edges.forEach((edge) => {
    if (edge.sourceHandle === 'params' && funcToParams[edge.target]) {
      const paramNode = paramNodes.find((p) => p.id === edge.source);
      if (paramNode) {
        funcToParams[edge.target].push(paramNode);
      }
    }
  });

  // Calculate group heights and positions
  const groups = [];
  const allNodes = [];
  let currentY = START_Y;

  functionNodes.forEach((funcNode) => {
    const orderIdx = orderMap[funcNode.id] || 0;
    const isLeft = orderIdx % 2 === 0;
    const connectedParams = funcToParams[funcNode.id] || [];

    // Calculate group dimensions - VERY LARGE for maximum readability
    const numParams = connectedParams.length;
    const paramsHeight = numParams * (PARAM_NODE_HEIGHT + PARAM_SPACING);
    const groupHeight = GROUP_PADDING * 2 + FUNC_NODE_HEIGHT + paramsHeight + 80; // Increased vertical padding
    const groupWidth = 1200; // MUCH LARGER - increased from 800

    const groupX = isLeft ? LEFT_X : RIGHT_X;
    const groupY = currentY;

    // Create group node
    const groupId = `group_${funcNode.id}`;
    const groupNode = {
      id: groupId,
      type: 'groupNode',
      position: { x: groupX, y: groupY },
      style: {
        width: groupWidth,
        height: groupHeight,
        backgroundColor: 'rgba(241, 245, 249, 0.8)',
        border: '2px dashed #94a3b8',
        borderRadius: '12px',
        padding: '10px',
      },
      data: {
        label: funcNode.data.customName || funcNode.data.functionName,
        functionName: funcNode.data.functionName,
        paramCount: numParams,
        description: funcNode.data.description || '', // Add description support
      },
    };
    groups.push(groupNode);

    // Position function node inside group
    const layoutedFunc = {
      ...funcNode,
      parentId: groupId,
      extent: 'parent',
      position: {
        x: GROUP_PADDING + 250,
        y: GROUP_PADDING,
      },
    };
    allNodes.push(layoutedFunc);

    // Position parameter nodes inside group, stacked vertically to the left
    connectedParams.forEach((paramNode, paramIdx) => {
      const layoutedParam = {
        ...paramNode,
        parentId: groupId,
        extent: 'parent',
        position: {
          x: GROUP_PADDING,
          y: GROUP_PADDING + FUNC_NODE_HEIGHT + 20 + (paramIdx * (PARAM_NODE_HEIGHT + PARAM_SPACING)),
        },
      };
      allNodes.push(layoutedParam);
    });

    // Update Y for next group
    currentY += groupHeight + 40;
  });

  // Add orphan parameter nodes (not connected to any function)
  const connectedParamIds = new Set();
  edges.forEach((edge) => {
    if (edge.sourceHandle === 'params') {
      connectedParamIds.add(edge.source);
    }
  });
  paramNodes.forEach((paramNode) => {
    if (!connectedParamIds.has(paramNode.id)) {
      allNodes.push({
        ...paramNode,
        position: { x: LEFT_X, y: currentY },
      });
      currentY += PARAM_NODE_HEIGHT + 20;
    }
  });

  return {
    nodes: [...groups, ...allNodes],
    edges,
  };
}

export default { getLayoutedNodes, createStaggeredLayout };

