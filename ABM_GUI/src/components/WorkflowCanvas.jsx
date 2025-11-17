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
import ParameterEditor from './ParameterEditor';
import useWorkflowStore from '../store/workflowStore';
import { getDefaultParameters } from '../data/functionRegistry';
import './WorkflowCanvas.css';

const nodeTypes = {
  workflowFunction: WorkflowFunctionNode,
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
  const [nodes, setNodes, onNodesChange] = useNodesState(stageNodes[stage] || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(stageEdges[stage] || []);

  // Track if we're syncing from store to prevent infinite loops
  const isSyncingFromStore = useRef(false);

  // Sync local state with store when store changes (e.g., workflow loaded)
  React.useEffect(() => {
    isSyncingFromStore.current = true;
    setNodes(stageNodes[stage] || []);
    // Reset flag after a tick to allow local changes to propagate
    setTimeout(() => {
      isSyncingFromStore.current = false;
    }, 0);
  }, [stageNodes[stage], setNodes]);

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
    (params) =>
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'smoothstep',
            animated: true,
            markerEnd: {
              type: 'arrowclosed',
              width: 20,
              height: 20,
            },
            style: {
              strokeWidth: 2,
            },
          },
          eds
        )
      ),
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const functionData = JSON.parse(event.dataTransfer.getData('application/reactflow'));

      if (!functionData) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const defaultParams = getDefaultParameters(functionData.name);
      const newId = `${functionData.name}_${Date.now()}`;
      const newNode = {
        id: newId,
        type: 'workflowFunction',
        position,
        data: {
          label: functionData.displayName,
          functionName: functionData.name,
          parameters: defaultParams,
          enabled: true,
          description: functionData.description,
          functionFile: defaultParams.function_file || '',
          onEdit: () => {
            setSelectedNode(newNode);
            setShowParameterEditor(true);
          },
        },
      };

      setNodes((nds) => nds.concat(newNode));
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
        // Update both parameters and custom name
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

