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
import ControllerSettings from './ControllerSettings';
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
  const [showControllerSettings, setShowControllerSettings] = useState(false);

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

  // Helper function to get Init node label based on stage
  const getInitNodeLabel = (stageName) => {
    // Capitalize first letter of stage name
    const capitalizedStage = stageName.charAt(0).toUpperCase() + stageName.slice(1);
    return `${capitalizedStage} Controller`;
  };

  // Ensure Init node is always present in the canvas
  React.useEffect(() => {
    const initNodeId = `init-${stage}`;
    const hasInitNode = nodes.some(n => n.id === initNodeId);

    if (!hasInitNode) {
      // Create Init node if it doesn't exist
      const initNode = {
        id: initNodeId,
        type: 'initNode',
        position: { x: 700, y: 50 }, // Top center position
        data: { label: getInitNodeLabel(stage) },
        deletable: false,
      };

      setNodes(prevNodes => [initNode, ...prevNodes]);
    }
  }, [stage, nodes, setNodes]);

  // Sync local state with store when store changes (e.g., workflow loaded)
  React.useEffect(() => {
    isSyncingFromStore.current = true;
    const newNodes = stageNodes[stage] || [];

    // Always ensure Init node is present
    const initNodeId = `init-${stage}`;
    const hasInitNode = newNodes.some(n => n.id === initNodeId);

    if (!hasInitNode) {
      // Add Init node if not present
      const initNode = {
        id: initNodeId,
        type: 'initNode',
        position: { x: 700, y: 50 },
        data: { label: getInitNodeLabel(stage) },
        deletable: false,
      };
      setNodes([initNode, ...newNodes]);
    } else {
      setNodes(newNodes);
    }

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

  // Track when steps-param is connected/disconnected and update controller node
  React.useEffect(() => {
    const initNodeId = `init-${stage}`;
    const stepsParamEdge = edges.find(
      (edge) => edge.targetHandle === 'steps-param' && edge.target === initNodeId
    );

    const isStepsParamConnected = !!stepsParamEdge;

    // Get the value from the connected parameter node
    let connectedStepsValue;
    if (stepsParamEdge) {
      const paramNode = nodes.find((n) => n.id === stepsParamEdge.source);
      if (paramNode && paramNode.data.parameters) {
        // Extract the steps value from the parameter node
        // Could be "steps" or "step_count" depending on the parameter
        connectedStepsValue = paramNode.data.parameters.steps ||
                             paramNode.data.parameters.step_count ||
                             paramNode.data.parameters.numberOfSteps;
      }
    }

    // Update the controller node's connection status and value
    setNodes((nds) =>
      nds.map((node) =>
        node.id === initNodeId
          ? {
              ...node,
              data: {
                ...node.data,
                isStepsParameterConnected: isStepsParamConnected,
                connectedStepsValue: connectedStepsValue,
              },
            }
          : node
      )
    );
  }, [edges, nodes, stage, setNodes]);

  const onConnect = useCallback(
    (params) => {
      // Determine connection type
      const isParameterConnection = params.sourceHandle === 'params' || params.targetHandle?.startsWith('params');
      const isInitConnection = params.sourceHandle === 'init-out';
      const isStepsParameterConnection = params.targetHandle === 'steps-param';

      // Determine edge color
      let strokeColor = undefined;
      if (isInitConnection) {
        strokeColor = '#dc2626'; // Red for Init connections
      } else if (isParameterConnection || isStepsParameterConnection) {
        strokeColor = '#3b82f6'; // Blue for parameter connections
      }

      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'default',
            animated: !isParameterConnection && !isStepsParameterConnection, // Animate function and init connections
            markerEnd: {
              type: 'arrowclosed',
              width: 10,
              height: 10,
              color: strokeColor,
            },
            style: {
              strokeWidth: isParameterConnection || isStepsParameterConnection ? 4 : 6,
              stroke: strokeColor,
            },
          },
          eds
        )
      );

      // If connecting to steps-param, update the controller node
      if (isStepsParameterConnection) {
        setNodes((nds) =>
          nds.map((node) =>
            node.id === params.target
              ? {
                  ...node,
                  data: {
                    ...node.data,
                    isStepsParameterConnected: true,
                  },
                }
              : node
          )
        );
      }
    },
    [setEdges, setNodes]
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
    // Open controller settings for Init nodes
    if (node.type === 'initNode') {
      setSelectedNode(node);
      setShowControllerSettings(true);
      return;
    }

    // Open parameter editor for other nodes
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

  const handleControllerSave = useCallback(
    (updatedData) => {
      if (selectedNode) {
        // Update the controller node's data
        setNodes((nds) =>
          nds.map((node) =>
            node.id === selectedNode.id
              ? {
                  ...node,
                  data: updatedData,
                }
              : node
          )
        );
        setShowControllerSettings(false);
      }
    },
    [selectedNode, setNodes]
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

      {showControllerSettings && selectedNode && (
        <ControllerSettings
          node={selectedNode}
          onSave={handleControllerSave}
          onClose={() => setShowControllerSettings(false)}
        />
      )}
    </div>
  );
};

export default WorkflowCanvas;

