import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import WorkflowFunctionNode from './WorkflowFunctionNode';
import ParameterNode from './ParameterNode';
import GroupNode from './GroupNode';
import InitNode from './InitNode';
import ParameterEditor from './ParameterEditor';
import useWorkflowStore from '../store/workflowStore';
import { getDefaultParameters } from '../data/functionRegistry';
import './WorkflowCanvas.css';

const nodeTypes = {
  workflowFunction: WorkflowFunctionNode,
  parameterNode: ParameterNode,
  groupNode: GroupNode,
  initNode: InitNode,
};

/**
 * Workflow Canvas - React Flow canvas for a specific stage
 */
const WorkflowCanvas = ({ stage }) => {
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showParameterEditor, setShowParameterEditor] = useState(false);

  const { stageNodes, stageEdges, setStageNodes, setStageEdges, updateFunctionParameters } =
    useWorkflowStore();

  // Initialize with current stage's nodes and edges
  const [nodes, setNodes, onNodesChangeBase] = useNodesState(stageNodes[stage] || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(stageEdges[stage] || []);

  // Wrap onNodesChange to prevent deletion of Init node
  const onNodesChange = useCallback((changes) => {
    // Filter out delete operations for Init nodes
    const filteredChanges = changes.filter(change => {
      if (change.type === 'remove' && change.id.startsWith('init-')) {
        console.log('[CANVAS] Prevented deletion of Init node');
        return false;
      }
      return true;
    });
    onNodesChangeBase(filteredChanges);
  }, [onNodesChangeBase]);

  // Track if we're syncing from store to prevent infinite loops
  const isSyncingFromStore = useRef(false);
  // Track if we've already fitted the view for this stage
  const hasFittedView = useRef({});

  // Sync local state with store when store changes (e.g., workflow loaded)
  React.useEffect(() => {
    isSyncingFromStore.current = true;
    const newNodes = stageNodes[stage] || [];
    setNodes(newNodes);

    // Reset flag after a tick to allow local changes to propagate
    setTimeout(() => {
      isSyncingFromStore.current = false;
      // Only fit view once when nodes are first loaded for this stage
      if (reactFlowInstance && newNodes.length > 0 && !hasFittedView.current[stage]) {
        reactFlowInstance.fitView({ padding: 0.2, duration: 200 });
        hasFittedView.current[stage] = true;
      }
    }, 0);
  }, [stageNodes[stage], setNodes, reactFlowInstance, stage]);

  React.useEffect(() => {
    isSyncingFromStore.current = true;
    setEdges(stageEdges[stage] || []);
    setTimeout(() => {
      isSyncingFromStore.current = false;
    }, 0);
  }, [stageEdges[stage], setEdges]);

  // Update store when nodes/edges change locally (drag, connect, etc.)
  React.useEffect(() => {
    if (!isSyncingFromStore.current) {
      setStageNodes(stage, nodes);
    }
  }, [nodes, stage, setStageNodes]);

  React.useEffect(() => {
    if (!isSyncingFromStore.current) {
      setStageEdges(stage, edges);
    }
  }, [edges, stage, setStageEdges]);

  const onConnect = useCallback(
    (params) => {
      // Determine connection type
      const isParameterConnection = params.sourceHandle === 'params' || params.targetHandle?.startsWith('params');
      const isInitConnection = params.sourceHandle === 'init-out';

      // Determine edge color
      let strokeColor = undefined;
      if (isInitConnection) {
        strokeColor = '#dc2626'; // Red for Init connections
      } else if (isParameterConnection) {
        strokeColor = '#3b82f6'; // Blue for parameter connections
      }

      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'default',
            animated: !isParameterConnection, // Animate function and init connections
            markerEnd: {
              type: 'arrowclosed',
              width: 20,
              height: 20,
              color: strokeColor,
            },
            style: {
              strokeWidth: isParameterConnection ? 4 : 6,
              stroke: strokeColor,
            },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const droppedData = JSON.parse(event.dataTransfer.getData('application/reactflow'));

      if (!droppedData) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Check if it's a parameter node
      if (droppedData.type === 'parameterNode') {
        const newId = `param_${Date.now()}`;
        const newNode = {
          id: newId,
          type: 'parameterNode',
          position,
          data: {
            label: droppedData.label || 'New Parameters',
            parameters: droppedData.parameters || {},
            onEdit: () => {
              setSelectedNode(newNode);
              setShowParameterEditor(true);
            },
          },
        };
        setNodes((nds) => nds.concat(newNode));
      } else {
        // It's a function node
        const defaultParams = getDefaultParameters(droppedData.name);
        const newId = `${droppedData.name}_${Date.now()}`;
        const newNode = {
          id: newId,
          type: 'workflowFunction',
          position,
          data: {
            label: droppedData.displayName,
            functionName: droppedData.name,
            parameters: defaultParams,
            enabled: true,
            description: droppedData.description,
            functionFile: defaultParams.function_file || '',
            onEdit: () => {
              setSelectedNode(newNode);
              setShowParameterEditor(true);
            },
          },
        };
        setNodes((nds) => nds.concat(newNode));
      }
    },
    [reactFlowInstance, setNodes]
  );

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  const onNodeDoubleClick = useCallback((event, node) => {
    setSelectedNode(node);
    setShowParameterEditor(true);
  }, []);

  const handleParameterSave = useCallback(
    (parameters, customName, customMetadata) => {
      if (selectedNode) {
        // For parameter nodes, just update label and parameters
        if (selectedNode.type === 'parameterNode') {
          setNodes((nds) =>
            nds.map((node) =>
              node.id === selectedNode.id
                ? {
                    ...node,
                    data: {
                      ...node.data,
                      label: customName || node.data.label,
                      parameters,
                    },
                  }
                : node
            )
          );
        } else {
          // For function nodes, update parameters and custom name in store
          updateFunctionParameters(stage, selectedNode.id, parameters, customName);

          // Also update the node's label and metadata in the local state
          setNodes((nds) =>
            nds.map((node) =>
              node.id === selectedNode.id
                ? {
                    ...node,
                    data: {
                      ...node.data,
                      parameters,
                      customName,
                      // Update step_count if provided
                      ...(customMetadata?.stepCount !== undefined && {
                        stepCount: customMetadata.stepCount,
                      }),
                      // For custom functions, also update function name, file, and description
                      ...(customMetadata && {
                        functionName: customMetadata.functionName,
                        functionFile: customMetadata.functionFile,
                        description: customMetadata.description,
                        label: customMetadata.functionName,
                      }),
                    },
                  }
                : node
            )
          );
        }

        setShowParameterEditor(false);
      }
    },
    [selectedNode, stage, updateFunctionParameters, setNodes]
  );

  return (
    <div className="workflow-canvas" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>

      {showParameterEditor && selectedNode && (
        <ParameterEditor
          node={selectedNode}
          onSave={handleParameterSave}
          onClose={() => setShowParameterEditor(false)}
        />
      )}
    </div>
  );
};

export default WorkflowCanvas;

