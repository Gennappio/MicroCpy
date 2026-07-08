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
 * - Init node is positioned at the top center
 * - Each function and its parameters are grouped in a visual container
 * - Groups are arranged vertically with staggered horizontal offsets
 * - Parameter nodes are displayed individually within the group
 *
 * @param {Array} functionNodes - Function nodes
 * @param {Array} paramNodes - Parameter nodes
 * @param {Array} edges - All edges
 * @param {Array} executionOrder - Order of function execution
 * @param {Object} initNode - The Init node (optional)
 * @returns {Object} - { nodes: layoutedNodes, edges: edges }
 */
export function createStaggeredLayout(functionNodes, paramNodes, edges, executionOrder = [], initNode = null) {
  // Layout constants
  const LEFT_X = 50;
  const RIGHT_X = 1400; // Offset for alternating groups
  const INIT_NODE_HEIGHT = 100; // Height reserved for Init node
  const INIT_SPACING = 60; // World between Init and first group
  const START_Y = initNode ? 50 + INIT_NODE_HEIGHT + INIT_SPACING : 50;
  const GROUP_PADDING = 80; // Padding inside group around nodes (increased for more world)
  const GROUP_MARGIN = 60; // Margin between nodes inside group (increased)
  const PARAM_NODE_WIDTH = 260; // Actual parameter node width
  const PARAM_NODE_HEIGHT = 80; // Actual parameter node height (with content)
  const FUNC_NODE_WIDTH = 350; // Fixed function node width (fits 40 characters)
  const FUNC_NODE_HEIGHT = 150; // Actual function node height
  const PARAM_SPACING = 20; // Vertical spacing between parameter nodes (increased)
  const HEADER_HEIGHT = 40; // Height reserved for title box
  const GROUP_VERTICAL_SPACING = 100; // Spacing between groups vertically (increased)

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
    currentY += groupHeight + GROUP_VERTICAL_SPACING;
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

  // Position the Init node at the top center if it exists
  const initNodes = [];
  if (initNode) {
    // Calculate the center position (between left and right groups)
    const initX = (LEFT_X + RIGHT_X) / 2 - 60; // Center the 120px wide Init node
    initNodes.push({
      ...initNode,
      position: { x: initX, y: 50 },
      style: {
        ...initNode.style,
        zIndex: 100, // Init node always on top
      },
    });
  }

  return {
    nodes: [...initNodes, ...groups, ...allNodes],
    edges,
  };
}

// Node classification for the "Tidy" auto-arrange button.
const TIDY_EXEC_TYPES = new Set(['workflowFunction', 'subworkflowCall', 'initNode', 'controllerNode']);
const TIDY_PARAM_TYPES = new Set(['parameterNode', 'listParameterNode', 'dictParameterNode']);
const TIDY_PARAM_SOURCES = new Set(['params', 'list-out', 'dict-out']);

// Per-type fallback sizes for nodes React Flow hasn't measured yet.
const TIDY_FALLBACK_DIMS = {
  workflowFunction: { width: 350, height: 160 },
  subworkflowCall: { width: 350, height: 140 },
  parameterNode: { width: 230, height: 110 },
  listParameterNode: { width: 230, height: 140 },
  dictParameterNode: { width: 230, height: 140 },
  initNode: { width: 200, height: 90 },
  controllerNode: { width: 200, height: 90 },
};
const TIDY_DEFAULT_DIMS = { width: 220, height: 100 };

const isExecNode = (n) => TIDY_EXEC_TYPES.has(n.type) || n.id.startsWith('controller-');
const isParamNode = (n) => TIDY_PARAM_TYPES.has(n.type);

function tidyDimsFor(node, measured) {
  const m = measured && measured.get(node.id);
  if (m && m.width && m.height) return { width: m.width, height: m.height };
  return TIDY_FALLBACK_DIMS[node.type] || TIDY_DEFAULT_DIMS;
}

/**
 * "Tidy" auto-arrange for a stage canvas.
 *
 * Lays the main branch (controller + the function/subworkflow-call nodes wired
 * to it) out as a single top-to-bottom column in execution order, dagre over the
 * func-out/init-out -> func-in edges only. Each node's parameter nodes are stacked
 * in a column to its LEFT, and dagre reserves enough vertical room per node for
 * that stack so adjacent nodes' params can't collide. Anything detached from the
 * controller (disconnected nodes, orphan params) is stacked in a column to the
 * RIGHT of the main branch. Only `position` is changed, so the export path (which
 * reads node.position) is unaffected.
 *
 * @param {Array} nodes - React Flow nodes
 * @param {Array} edges - React Flow edges
 * @param {Map<string,{width:number,height:number}>} measured - measured sizes by node id
 * @param {Object} options - spacing overrides
 * @returns {Array} - nodes with updated positions
 */
export function getTidyLayout(nodes, edges, measured, options = {}) {
  const {
    rankSpacing = 120,
    nodeSpacing = 80,
    paramGap = 60,
    paramSpacing = 20,
    branchGap = 180, // horizontal gap between the main branch and the detached column
    stackGap = 60, // vertical gap between stacked detached items
  } = options;

  const execNodes = nodes.filter(isExecNode);
  const paramNodes = nodes.filter(isParamNode);
  if (execNodes.length === 0) return nodes; // nothing to arrange (defensive)

  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const dimsById = (id) => tidyDimsFor(nodeById.get(id), measured);
  const execIds = new Set(execNodes.map((n) => n.id));

  // Map each parameter node to the execution node it feeds (first owner wins).
  const ownerOf = {};
  const paramsByOwner = {};
  edges.forEach((edge) => {
    if (!TIDY_PARAM_SOURCES.has(edge.sourceHandle) || !execIds.has(edge.target) || ownerOf[edge.source]) {
      return;
    }
    const paramNode = paramNodes.find((n) => n.id === edge.source);
    if (!paramNode) return;
    ownerOf[edge.source] = edge.target;
    (paramsByOwner[edge.target] = paramsByOwner[edge.target] || []).push(paramNode);
  });

  const paramStackHeight = (ownerId) => {
    const ps = paramsByOwner[ownerId];
    if (!ps || ps.length === 0) return 0;
    return ps.reduce((sum, p) => sum + tidyDimsFor(p, measured).height, 0) + (ps.length - 1) * paramSpacing;
  };
  const paramStackWidth = (ownerId) => {
    const ps = paramsByOwner[ownerId];
    if (!ps || ps.length === 0) return 0;
    return Math.max(...ps.map((p) => tidyDimsFor(p, measured).width));
  };

  const newPos = {};

  // Stack an owner's parameter column immediately to its left, centered on it.
  const placeParamsLeft = (ownerId, ownerX, ownerCy) => {
    const params = paramsByOwner[ownerId];
    if (!params) return;
    const colWidth = paramStackWidth(ownerId);
    const x = ownerX - paramGap - colWidth;
    let y = ownerCy - paramStackHeight(ownerId) / 2;
    params.forEach((p) => {
      newPos[p.id] = { x, y };
      y += tidyDimsFor(p, measured).height + paramSpacing;
    });
  };

  // Split execution nodes into the controller's connected "main branch" and
  // everything detached from it (walk execution edges as undirected).
  const execEdges = edges.filter(
    (e) =>
      (e.sourceHandle === 'func-out' || e.sourceHandle === 'init-out') &&
      execIds.has(e.source) &&
      execIds.has(e.target)
  );
  const adjacency = {};
  execEdges.forEach((e) => {
    (adjacency[e.source] = adjacency[e.source] || []).push(e.target);
    (adjacency[e.target] = adjacency[e.target] || []).push(e.source);
  });
  const controller = execNodes.find(
    (n) => n.type === 'controllerNode' || n.type === 'initNode' || n.id.startsWith('controller-')
  );
  const mainSet = new Set();
  if (controller) {
    const queue = [controller.id];
    mainSet.add(controller.id);
    while (queue.length) {
      const cur = queue.shift();
      (adjacency[cur] || []).forEach((nb) => {
        if (!mainSet.has(nb)) {
          mainSet.add(nb);
          queue.push(nb);
        }
      });
    }
  }
  const mainExec = mainSet.size ? execNodes.filter((n) => mainSet.has(n.id)) : execNodes;
  const mainIds = new Set(mainExec.map((n) => n.id));
  const detachedExec = execNodes.filter((n) => !mainIds.has(n.id));

  // Dagre top-to-bottom over the main branch. Reserve vertical room for each
  // node's parameter stack so params of adjacent nodes can't collide.
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: nodeSpacing, ranksep: rankSpacing, marginx: 40, marginy: 40 });
  mainExec.forEach((node) => {
    const d = tidyDimsFor(node, measured);
    dagreGraph.setNode(node.id, { width: d.width, height: Math.max(d.height, paramStackHeight(node.id)) });
  });
  execEdges.forEach((e) => {
    if (mainIds.has(e.source) && mainIds.has(e.target)) dagreGraph.setEdge(e.source, e.target);
  });
  dagre.layout(dagreGraph);

  mainExec.forEach((node) => {
    const gp = dagreGraph.node(node.id);
    const d = tidyDimsFor(node, measured);
    const x = gp.x - d.width / 2;
    newPos[node.id] = { x, y: gp.y - d.height / 2 };
    placeParamsLeft(node.id, x, gp.y);
  });

  // Bounding box of the main branch as placed so far (execution nodes + params).
  const placedIds = Object.keys(newPos);
  let rightEdge = -Infinity;
  let topEdge = Infinity;
  placedIds.forEach((id) => {
    rightEdge = Math.max(rightEdge, newPos[id].x + dimsById(id).width);
    topEdge = Math.min(topEdge, newPos[id].y);
  });
  if (!Number.isFinite(rightEdge)) {
    rightEdge = 0;
    topEdge = 0;
  }

  // Detached nodes (with their params) and orphan params go in a column to the
  // RIGHT of the main branch, stacked vertically, so they never overlap it.
  const orphanParams = paramNodes.filter((p) => !ownerOf[p.id]);
  if (detachedExec.length > 0 || orphanParams.length > 0) {
    const maxDetachedParamWidth = detachedExec.reduce((m, n) => Math.max(m, paramStackWidth(n.id)), 0);
    const colX = rightEdge + branchGap + (maxDetachedParamWidth ? maxDetachedParamWidth + paramGap : 0);
    let stackY = topEdge;

    detachedExec.forEach((node) => {
      const d = tidyDimsFor(node, measured);
      const slotHeight = Math.max(d.height, paramStackHeight(node.id));
      const cy = stackY + slotHeight / 2;
      newPos[node.id] = { x: colX, y: cy - d.height / 2 };
      placeParamsLeft(node.id, colX, cy);
      stackY += slotHeight + stackGap;
    });

    orphanParams.forEach((p) => {
      newPos[p.id] = { x: colX, y: stackY };
      stackY += tidyDimsFor(p, measured).height + paramSpacing;
    });
  }

  // Position-only result; clear any stray parent linkage so coordinates stay absolute.
  return nodes.map((n) =>
    newPos[n.id] ? { ...n, position: newPos[n.id], parentId: undefined, extent: undefined } : n
  );
}

export default { getLayoutedNodes, createStaggeredLayout, getTidyLayout };

