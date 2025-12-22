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
  // Layout constants - MUCH LARGER for better readability
  const LEFT_X = 50;
  const RIGHT_X = 1000;
  const START_Y = 50;
  const GROUP_PADDING = 50;
  const PARAM_NODE_HEIGHT = 120;
  const PARAM_NODE_WIDTH = 450;
  const FUNC_NODE_HEIGHT = 180;
  const FUNC_NODE_WIDTH = 380;
  const PARAM_SPACING = 25;
  const VERTICAL_GAP_BETWEEN_GROUPS = 100;

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

    // Calculate group dimensions based on number of parameters
    const numParams = connectedParams.length;
    const paramsHeight = numParams > 0 ? numParams * (PARAM_NODE_HEIGHT + PARAM_SPACING) - PARAM_SPACING : 0;
    const groupHeight = GROUP_PADDING * 2 + FUNC_NODE_HEIGHT + (numParams > 0 ? 30 + paramsHeight : 0);
    const groupWidth = GROUP_PADDING * 2 + Math.max(PARAM_NODE_WIDTH, FUNC_NODE_WIDTH + 50);

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
        backgroundColor: 'rgba(241, 245, 249, 0.9)',
        border: '3px dashed #64748b',
        borderRadius: '16px',
        padding: `${GROUP_PADDING}px`,
      },
      data: {
        label: funcNode.data.customName || funcNode.data.functionName,
        functionName: funcNode.data.functionName,
        paramCount: numParams,
      },
    };
    groups.push(groupNode);

    // Position function node inside group at the top
    const layoutedFunc = {
      ...funcNode,
      parentId: groupId,
      extent: 'parent',
      position: {
        x: GROUP_PADDING + 20,
        y: GROUP_PADDING,
      },
    };
    allNodes.push(layoutedFunc);

    // Position parameter nodes inside group, stacked vertically below function
    connectedParams.forEach((paramNode, paramIdx) => {
      const layoutedParam = {
        ...paramNode,
        parentId: groupId,
        extent: 'parent',
        position: {
          x: GROUP_PADDING,
          y: GROUP_PADDING + FUNC_NODE_HEIGHT + 25 + (paramIdx * (PARAM_NODE_HEIGHT + PARAM_SPACING)),
        },
      };
      allNodes.push(layoutedParam);
    });

    // Update Y for next group
    currentY += groupHeight + VERTICAL_GAP_BETWEEN_GROUPS;
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

