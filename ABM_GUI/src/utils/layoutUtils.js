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
  const RIGHT_X = 1300; // Offset for alternating groups
  const START_Y = 50;
  const GROUP_PADDING = 60; // Padding inside group around nodes
  const GROUP_MARGIN = 30; // Margin between nodes inside group
  const PARAM_NODE_WIDTH = 260; // Actual parameter node width
  const PARAM_NODE_HEIGHT = 80; // Actual parameter node height (with content)
  const FUNC_NODE_WIDTH = 240; // Actual function node width
  const FUNC_NODE_HEIGHT = 200; // Actual function node height (with parameters list)
  const PARAM_SPACING = 15; // Vertical spacing between parameter nodes
  const HEADER_HEIGHT = 40; // Height reserved for title box

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

    // Calculate group dimensions dynamically based on content
    const numParams = connectedParams.length;
    const paramsStackHeight = numParams > 0
      ? numParams * PARAM_NODE_HEIGHT + (numParams - 1) * PARAM_SPACING
      : 0;

    // Group height: padding top + header + max(params stack, func node) + padding bottom
    const contentHeight = Math.max(paramsStackHeight, FUNC_NODE_HEIGHT);
    const groupHeight = GROUP_PADDING + HEADER_HEIGHT + contentHeight + GROUP_PADDING;

    // Group width: padding + params + margin + func + padding
    const groupWidth = GROUP_PADDING + PARAM_NODE_WIDTH + GROUP_MARGIN + FUNC_NODE_WIDTH + GROUP_PADDING;

    const groupX = isLeft ? LEFT_X : RIGHT_X;
    const groupY = currentY;

    // Create group node - draggable container
    const groupId = `group_${funcNode.id}`;
    const groupNode = {
      id: groupId,
      type: 'groupNode',
      position: { x: groupX, y: groupY },
      style: {
        width: groupWidth,
        height: groupHeight,
        zIndex: -100, // NEGATIVE z-index to ensure group is behind EVERYTHING including edges
      },
      data: {
        label: funcNode.data.customName || funcNode.data.functionName,
        functionName: funcNode.data.functionName,
        paramCount: numParams,
        description: funcNode.data.description || '',
      },
      selectable: true, // Make group selectable
      draggable: true, // Make group draggable - children will move with it
    };
    groups.push(groupNode);

    // Position function node inside group (on the right side)
    const funcX = GROUP_PADDING + PARAM_NODE_WIDTH + GROUP_MARGIN;
    const funcY = GROUP_PADDING + HEADER_HEIGHT;

    const layoutedFunc = {
      ...funcNode,
      parentId: groupId,
      extent: 'parent', // Constrain to parent bounds
      position: {
        x: funcX,
        y: funcY,
      },
      style: {
        ...funcNode.style,
        zIndex: 10,
      },
    };
    allNodes.push(layoutedFunc);

    // Position parameter nodes inside group, stacked vertically on the left
    connectedParams.forEach((paramNode, paramIdx) => {
      const paramX = GROUP_PADDING;
      const paramY = GROUP_PADDING + HEADER_HEIGHT + (paramIdx * (PARAM_NODE_HEIGHT + PARAM_SPACING));

      const layoutedParam = {
        ...paramNode,
        parentId: groupId,
        extent: 'parent', // Constrain to parent bounds
        position: {
          x: paramX,
          y: paramY,
        },
        style: {
          ...paramNode.style,
          zIndex: 10,
        },
      };
      allNodes.push(layoutedParam);
    });

    // Update Y for next group with gap between groups
    currentY += groupHeight + 60;
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

