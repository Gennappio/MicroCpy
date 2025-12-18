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
	      initialization: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      macrostep: { enabled: false, steps: 1, functions: [], execution_order: [] },
	      intracellular: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      microenvironment: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      intercellular: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      finalization: { enabled: true, steps: 1, functions: [], execution_order: [] },
	    },
  },

  // Current active stage
  currentStage: 'initialization',

  // React Flow nodes and edges for each stage
  stageNodes: {
    initialization: [],
    macrostep: [],
    intracellular: [],
    microenvironment: [],
    intercellular: [],
    finalization: [],
  },

  stageEdges: {
    initialization: [],
    macrostep: [],
    intracellular: [],
    microenvironment: [],
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
      macrostep: [],
      intracellular: [],
      microenvironment: [],
      intercellular: [],
      finalization: [],
    };
    const newStageEdges = {
      initialization: [],
      macrostep: [],
      intracellular: [],
      microenvironment: [],
      intercellular: [],
      finalization: [],
    };

    // Layout constants for tidy positioning
    const FUNC_NODE_X = 350;           // X position for function nodes
    const PARAM_NODE_X = 50;           // X position for parameter nodes (to the left)
    const START_Y = 50;                // Starting Y position
    const FUNC_NODE_SPACING = 120;     // Vertical spacing between function nodes
    const PARAM_NODE_OFFSET_Y = 10;    // Y offset for param node relative to function

    // Convert workflow functions and parameter nodes to React Flow nodes for ALL stages
    Object.keys(newStageNodes).forEach((stageName) => {
      // Handle backward compatibility: "diffusion" -> "microenvironment"
      const actualStageName = stageName === 'microenvironment' && !stages[stageName] && stages['diffusion']
        ? 'diffusion'
        : stageName;
      const stage = stages[actualStageName];
      if (!stage) return;

      const allNodes = [];
      const allEdges = [];
      const createdParamNodeIds = new Set(); // Track created parameter nodes

      // Build execution order index map for positioning
      const executionOrder = stage.execution_order || [];
      const orderIndexMap = {};
      executionOrder.forEach((funcId, idx) => {
        orderIndexMap[funcId] = idx;
      });

      // For functions not in execution_order, assign indices after the ordered ones
      let nextUnorderedIdx = executionOrder.length;
      stage.functions.forEach((func) => {
        if (!(func.id in orderIndexMap)) {
          orderIndexMap[func.id] = nextUnorderedIdx++;
        }
      });

      // Create parameter nodes from the parameters array (if exists)
      // Position them based on linked function positions
      const explicitParamNodes = (stage.parameters || []).map((param, idx) => ({
        id: param.id,
        type: 'parameterNode',
        position: param.position || { x: PARAM_NODE_X, y: START_Y + idx * FUNC_NODE_SPACING },
        data: {
          label: param.label || 'Parameters',
          parameters: param.parameters || {},
          onEdit: () => {}, // Will be set by WorkflowCanvas
        },
      }));
      explicitParamNodes.forEach(node => createdParamNodeIds.add(node.id));
      allNodes.push(...explicitParamNodes);

      // Auto-create parameter nodes for functions that have parameters but no parameter_nodes connections
      const autoCreatedParamNodes = [];
      stage.functions.forEach((func) => {
        const hasParameters = func.parameters && Object.keys(func.parameters).length > 0;
        const hasParamNodeConnections = func.parameter_nodes && func.parameter_nodes.length > 0;

        // If function has parameters but no parameter node connections, create a parameter node
        if (hasParameters && !hasParamNodeConnections) {
          const paramNodeId = `param_auto_${func.id}`;
          const funcOrderIdx = orderIndexMap[func.id] || 0;
          const funcY = START_Y + funcOrderIdx * FUNC_NODE_SPACING;

          const paramNode = {
            id: paramNodeId,
            type: 'parameterNode',
            position: {
              // Parameter nodes positioned to the LEFT of function nodes
              x: PARAM_NODE_X,
              y: funcY + PARAM_NODE_OFFSET_Y
            },
            data: {
              label: `${func.custom_name || func.function_name} Parameters`,
              parameters: func.parameters || {},
              onEdit: () => {}, // Will be set by WorkflowCanvas
            },
          };
          autoCreatedParamNodes.push(paramNode);
          createdParamNodeIds.add(paramNodeId);

          // Update the function to reference this parameter node
          if (!func.parameter_nodes) {
            func.parameter_nodes = [];
          }
          func.parameter_nodes.push(paramNodeId);
        }
      });
      allNodes.push(...autoCreatedParamNodes);

      // Create function nodes - use execution order for Y positioning
      const functionNodes = stage.functions.map((func) => {
        const orderIdx = orderIndexMap[func.id] || 0;
        const defaultY = START_Y + orderIdx * FUNC_NODE_SPACING;

        return {
          id: func.id,
          type: 'workflowFunction',
          position: func.position || { x: FUNC_NODE_X, y: defaultY },
          data: {
            label: func.function_name,
            functionName: func.function_name,
            // Preserve function-level parameters (e.g., config_file) so they survive export
            parameters: func.parameters || {},
            enabled: func.enabled !== false,
            description: func.description || '',
            functionFile: func.function_file || func.parameters?.function_file || '',
            customName: func.custom_name || '',
            stepCount: func.step_count || 1, // NEW: Load step_count from JSON
            onEdit: () => {}, // Will be set by WorkflowCanvas
          },
        };
      });
      allNodes.push(...functionNodes);

      // Create parameter connection edges
      stage.functions.forEach((func) => {
        if (func.parameter_nodes && Array.isArray(func.parameter_nodes)) {
          func.parameter_nodes.forEach((paramNodeId) => {
            allEdges.push({
              id: `e-param-${paramNodeId}-${func.id}`,
              source: paramNodeId,
              sourceHandle: 'params',
              target: func.id,
              targetHandle: 'params',
              type: 'smoothstep',
              animated: false,
              markerEnd: {
                type: 'arrowclosed',
                width: 20,
                height: 20,
              },
              style: {
                strokeWidth: 2,
                stroke: '#3b82f6', // Blue for parameter connections
              },
            });
          });
        }
      });

      // Create function flow edges based on execution order
      for (let i = 0; i < stage.execution_order.length - 1; i++) {
        allEdges.push({
          id: `e-${stage.execution_order[i]}-${stage.execution_order[i + 1]}`,
          source: stage.execution_order[i],
          sourceHandle: 'func-out',
          target: stage.execution_order[i + 1],
          targetHandle: 'func-in',
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

      newStageNodes[stageName] = allNodes;
      newStageEdges[stageName] = allEdges;
    });

	    set((state) => ({
	      workflow: {
	        ...state.workflow,
	        ...workflowJson,
	        stages: {
	          ...state.workflow.stages,
	          ...Object.keys(newStageNodes).reduce((acc, stageName) => {
	            const srcStages = workflowJson.stages || {};
	            const srcStage = srcStages[stageName] || {};
	            acc[stageName] = {
	              ...state.workflow.stages[stageName],
	              ...srcStage,
	              steps:
	                srcStage.steps != null
	                  ? srcStage.steps
	                  : state.workflow.stages[stageName]?.steps || 1,
	            };
	            return acc;
	          }, {}),
	        },
	      },
	      stageNodes: newStageNodes,
	      stageEdges: newStageEdges,
	    }));
  },

	  // Toggle whether a whole stage is enabled (e.g. macrostep)
	  toggleStageEnabled: (stageName) =>
	    set((state) => {
	      const currentEnabled = state.workflow.stages[stageName]?.enabled !== false;
	      return {
	        workflow: {
	          ...state.workflow,
	          stages: {
	            ...state.workflow.stages,
	            [stageName]: {
	              ...state.workflow.stages[stageName],
	              enabled: !currentEnabled,
	            },
	          },
	        },
	      };
	    }),

  // Export workflow to JSON
  exportWorkflow: () => {
    const state = get();
    const { workflow, stageNodes, stageEdges } = state;

    // Convert React Flow nodes back to workflow functions and parameter nodes
    const stages = {};
    Object.keys(workflow.stages).forEach((stageName) => {
      const nodes = stageNodes[stageName] || [];
      const edges = stageEdges[stageName] || [];

      // Separate function nodes and parameter nodes
      const functionNodes = nodes.filter(n => n.type === 'workflowFunction');
      const parameterNodes = nodes.filter(n => n.type === 'parameterNode');

      // Export function nodes
      const functions = functionNodes.map((node) => {
        // Find parameter connections for this function
        const parameterConnections = edges
          .filter(e => e.target === node.id && e.targetHandle === 'params')
          .map(e => e.source); // IDs of connected parameter nodes

        return {
          id: node.id,
          function_name: node.data.functionName,
          function_file: node.data.functionFile || node.data.parameters?.function_file || '',
          parameters: node.data.parameters || {},
          enabled: node.data.enabled !== false,
          position: node.position,
          description: node.data.description || '',
          custom_name: node.data.customName || '',
          step_count: node.data.stepCount || 1, // NEW: Save step_count to JSON
          parameter_nodes: parameterConnections, // NEW: IDs of connected parameter nodes
        };
      });

      // Export parameter nodes
      const parameters = parameterNodes.map((node) => ({
        id: node.id,
        label: node.data.label || 'Parameters',
        parameters: node.data.parameters || {},
        position: node.position,
      }));

      // Execution order from function flow edges only
      const functionEdges = edges.filter(e => e.sourceHandle === 'func-out' || !e.sourceHandle);
      const execution_order = functionNodes.map((n) => n.id); // Simple order for now

	      stages[stageName] = {
	        enabled: workflow.stages[stageName]?.enabled !== false,
	        steps: workflow.stages[stageName]?.steps || 1,
	        functions,
	        parameters, // NEW: Parameter nodes
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

	  // Toggle whether a specific function node is enabled (by node id)
	  toggleFunctionEnabled: (nodeId) =>
	    set((state) => {
	      const newStageNodes = {};
	      Object.keys(state.stageNodes).forEach((stageName) => {
	        newStageNodes[stageName] = state.stageNodes[stageName].map((node) =>
	          node.id === nodeId
	            ? {
	                ...node,
	                data: {
	                  ...node.data,
	                  enabled: node.data.enabled === false,
	                },
	              }
	            : node
	        );
	      });
	      return { stageNodes: newStageNodes };
	    }),

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
  updateFunctionParameters: (stage, nodeId, parameters, customName) =>
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
                  customName: customName || node.data.customName,
                },
              }
            : node
        ),
      },
    })),

	  // Update stage steps (e.g. number of macrosteps)
	  setStageSteps: (stageName, steps) =>
	    set((state) => ({
	      workflow: {
	        ...state.workflow,
	        stages: {
	          ...state.workflow.stages,
	          [stageName]: {
	            ...state.workflow.stages[stageName],
	            steps,
	          },
	        },
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
	          initialization: { enabled: true, steps: 1, functions: [], execution_order: [] },
	          macrostep: { enabled: false, steps: 1, functions: [], execution_order: [] },
	          intracellular: { enabled: true, steps: 1, functions: [], execution_order: [] },
	          microenvironment: { enabled: true, steps: 1, functions: [], execution_order: [] },
	          intercellular: { enabled: true, steps: 1, functions: [], execution_order: [] },
	          finalization: { enabled: true, steps: 1, functions: [], execution_order: [] },
        },
      },
      stageNodes: {
        initialization: [],
        macrostep: [],
        intracellular: [],
        microenvironment: [],
        intercellular: [],
        finalization: [],
      },
      stageEdges: {
        initialization: [],
        macrostep: [],
        intracellular: [],
        microenvironment: [],
        intercellular: [],
        finalization: [],
      },
    }),
}));

export default useWorkflowStore;

