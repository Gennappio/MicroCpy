import { create } from 'zustand';

/**
 * Workflow Store - Manages the entire workflow state
 * Compatible with MicroC workflow JSON format
 */
const useWorkflowStore = create((set, get) => ({
  // Workflow metadata
  workflow: {
    version: '1.0',
    name: 'Untitled Workflow',
    description: '',
    metadata: {
      author: '',
      created: new Date().toISOString().split('T')[0],
    },
    stages: {
      initialization: { enabled: true, functions: [], execution_order: [] },
      intracellular: { enabled: true, functions: [], execution_order: [] },
      diffusion: { enabled: true, functions: [], execution_order: [] },
      intercellular: { enabled: true, functions: [], execution_order: [] },
      finalization: { enabled: true, functions: [], execution_order: [] },
    },
  },

  // Current active stage
  currentStage: 'initialization',

  // React Flow nodes and edges for each stage
  stageNodes: {
    initialization: [],
    intracellular: [],
    diffusion: [],
    intercellular: [],
    finalization: [],
  },

  stageEdges: {
    initialization: [],
    intracellular: [],
    diffusion: [],
    intercellular: [],
    finalization: [],
  },

  // Actions
  setCurrentStage: (stage) => set({ currentStage: stage }),

  setWorkflowMetadata: (metadata) =>
    set((state) => ({
      workflow: {
        ...state.workflow,
        ...metadata,
      },
    })),

  // Load workflow from JSON - LOADS ALL STAGES
  loadWorkflow: (workflowJson) => {
    const { stages } = workflowJson;
    const newStageNodes = {
      initialization: [],
      intracellular: [],
      diffusion: [],
      intercellular: [],
      finalization: [],
    };
    const newStageEdges = {
      initialization: [],
      intracellular: [],
      diffusion: [],
      intercellular: [],
      finalization: [],
    };

    // Convert workflow functions to React Flow nodes for ALL stages
    Object.keys(newStageNodes).forEach((stageName) => {
      const stage = stages[stageName];
      if (!stage) return;

      const nodes = stage.functions.map((func) => ({
        id: func.id,
        type: 'workflowFunction',
        position: func.position || { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
        data: {
          label: func.function_name,
          functionName: func.function_name,
          parameters: func.parameters || {},
          enabled: func.enabled !== false,
          description: func.description || '',
          functionFile: func.function_file || func.parameters?.function_file || '',
        },
      }));

      // Create edges based on execution order with ARROWS (markerEnd)
      const edges = [];
      for (let i = 0; i < stage.execution_order.length - 1; i++) {
        edges.push({
          id: `e-${stage.execution_order[i]}-${stage.execution_order[i + 1]}`,
          source: stage.execution_order[i],
          target: stage.execution_order[i + 1],
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
        });
      }

      newStageNodes[stageName] = nodes;
      newStageEdges[stageName] = edges;
    });

    set({
      workflow: workflowJson,
      stageNodes: newStageNodes,
      stageEdges: newStageEdges,
    });
  },

  // Export workflow to JSON
  exportWorkflow: () => {
    const state = get();
    const { workflow, stageNodes } = state;

    // Convert React Flow nodes back to workflow functions
    const stages = {};
    Object.keys(workflow.stages).forEach((stageName) => {
      const nodes = stageNodes[stageName] || [];
      const functions = nodes.map((node) => ({
        id: node.id,
        function_name: node.data.functionName,
        function_file: node.data.functionFile || node.data.parameters?.function_file || '',
        parameters: node.data.parameters || {},
        enabled: node.data.enabled !== false,
        position: node.position,
        description: node.data.description || '',
      }));

      // Execution order from edges (topological sort)
      const edges = state.stageEdges[stageName] || [];
      const execution_order = nodes.map((n) => n.id); // Simple order for now

      stages[stageName] = {
        enabled: workflow.stages[stageName]?.enabled !== false,
        functions,
        execution_order,
      };
    });

    return {
      ...workflow,
      stages,
    };
  },

  // Update nodes for a stage
  setStageNodes: (stage, nodes) =>
    set((state) => ({
      stageNodes: {
        ...state.stageNodes,
        [stage]: nodes,
      },
    })),

  // Update edges for a stage
  setStageEdges: (stage, edges) =>
    set((state) => ({
      stageEdges: {
        ...state.stageEdges,
        [stage]: edges,
      },
    })),

  // Add a function to a stage
  addFunction: (stage, functionData) => {
    const state = get();
    const nodes = state.stageNodes[stage] || [];
    const newId = `${functionData.function_name}_${Date.now()}`;

    const newNode = {
      id: newId,
      type: 'workflowFunction',
      position: functionData.position || { x: 100, y: 100 },
      data: {
        label: functionData.function_name,
        functionName: functionData.function_name,
        parameters: functionData.parameters || {},
        enabled: true,
        description: functionData.description || '',
      },
    };

    set((state) => ({
      stageNodes: {
        ...state.stageNodes,
        [stage]: [...nodes, newNode],
      },
    }));

    return newId;
  },

  // Remove a function from a stage
  removeFunction: (stage, nodeId) =>
    set((state) => ({
      stageNodes: {
        ...state.stageNodes,
        [stage]: state.stageNodes[stage].filter((n) => n.id !== nodeId),
      },
      stageEdges: {
        ...state.stageEdges,
        [stage]: state.stageEdges[stage].filter(
          (e) => e.source !== nodeId && e.target !== nodeId
        ),
      },
    })),

  // Update function parameters
  updateFunctionParameters: (stage, nodeId, parameters) =>
    set((state) => ({
      stageNodes: {
        ...state.stageNodes,
        [stage]: state.stageNodes[stage].map((node) =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  parameters: { ...node.data.parameters, ...parameters },
                },
              }
            : node
        ),
      },
    })),

  // Clear all workflow data
  clearWorkflow: () =>
    set({
      workflow: {
        version: '1.0',
        name: 'Untitled Workflow',
        description: '',
        metadata: {
          author: '',
          created: new Date().toISOString().split('T')[0],
        },
        stages: {
          initialization: { enabled: true, functions: [], execution_order: [] },
          intracellular: { enabled: true, functions: [], execution_order: [] },
          diffusion: { enabled: true, functions: [], execution_order: [] },
          intercellular: { enabled: true, functions: [], execution_order: [] },
          finalization: { enabled: true, functions: [], execution_order: [] },
        },
      },
      stageNodes: {
        initialization: [],
        intracellular: [],
        diffusion: [],
        intercellular: [],
        finalization: [],
      },
      stageEdges: {
        initialization: [],
        intracellular: [],
        diffusion: [],
        intercellular: [],
        finalization: [],
      },
    }),
}));

export default useWorkflowStore;

