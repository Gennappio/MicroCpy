import { create } from 'zustand';
import { createStaggeredLayout } from '../utils/layoutUtils';

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

    // Convert workflow functions and parameter nodes to React Flow nodes for ALL stages
    // Uses staggered layout for visual arrangement
    Object.keys(newStageNodes).forEach((stageName) => {
      // Handle backward compatibility: "diffusion" -> "microenvironment"
      const actualStageName = stageName === 'microenvironment' && !stages[stageName] && stages['diffusion']
        ? 'diffusion'
        : stageName;
      const stage = stages[actualStageName];
      if (!stage) return;

      const allEdges = [];
      const createdParamNodeIds = new Set(); // Track created parameter nodes

      // Build execution order for layout
      const executionOrder = stage.execution_order || [];

      // Create parameter nodes from the parameters array (if exists)
      // Positions will be set by staggered layout
      const explicitParamNodes = (stage.parameters || []).map((param) => ({
        id: param.id,
        type: 'parameterNode',
        position: param.position || { x: 0, y: 0 }, // Will be set by staggered layout
        data: {
          label: param.label || 'Parameters',
          parameters: param.parameters || {},
          onEdit: () => {}, // Will be set by WorkflowCanvas
        },
      }));
      explicitParamNodes.forEach(node => createdParamNodeIds.add(node.id));

      // Auto-create parameter nodes for functions that have parameters but no parameter_nodes connections
      const autoCreatedParamNodes = [];
      stage.functions.forEach((func) => {
        const hasParameters = func.parameters && Object.keys(func.parameters).length > 0;
        const hasParamNodeConnections = func.parameter_nodes && func.parameter_nodes.length > 0;

        // If function has parameters but no parameter node connections, create a parameter node
        if (hasParameters && !hasParamNodeConnections) {
          const paramNodeId = `param_auto_${func.id}`;

          const paramNode = {
            id: paramNodeId,
            type: 'parameterNode',
            position: { x: 0, y: 0 }, // Will be set by staggered layout
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

      // Create the Init node - always present in every stage
      const initNodeId = `init-${stageName}`;
      const initNode = {
        id: initNodeId,
        type: 'initNode',
        position: { x: 0, y: 0 }, // Will be set by layout
        data: {
          label: 'INIT',
        },
        deletable: false, // Cannot be deleted
      };

      // Create function nodes (positions will be set by staggered layout)
      const functionNodes = stage.functions.map((func) => {
        return {
          id: func.id,
          type: 'workflowFunction',
          position: func.position || { x: 0, y: 0 }, // Will be overwritten by layout
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

      // Create parameter connection edges - one edge per parameter node with unique target handle
      stage.functions.forEach((func) => {
        if (func.parameter_nodes && Array.isArray(func.parameter_nodes)) {
          func.parameter_nodes.forEach((paramNodeId, index) => {
            allEdges.push({
              id: `e-param-${paramNodeId}-${func.id}`,
              source: paramNodeId,
              sourceHandle: 'params',
              target: func.id,
              targetHandle: `params-${index}`, // Unique handle for each parameter connection
              type: 'default', // Bezier curve (smooth)
              animated: false,
              markerEnd: {
                type: 'arrowclosed',
                width: 20,
                height: 20,
                color: '#3b82f6', // Blue arrow tip
              },
              style: {
                strokeWidth: 4,
                stroke: '#3b82f6', // Blue for parameter connections
              },
            });
          });
        }
      });

      // Create edge from Init to first function in execution order (if any)
      if (stage.execution_order.length > 0) {
        allEdges.push({
          id: `e-init-${stage.execution_order[0]}`,
          source: initNodeId,
          sourceHandle: 'init-out',
          target: stage.execution_order[0],
          targetHandle: 'func-in',
          type: 'default',
          animated: true,
          markerEnd: {
            type: 'arrowclosed',
            width: 20,
            height: 20,
            color: '#dc2626', // Red arrow tip to match Init node
          },
          style: {
            strokeWidth: 6,
            stroke: '#dc2626', // Red edge from Init
          },
        });
      }

      // Create function flow edges based on execution order
      for (let i = 0; i < stage.execution_order.length - 1; i++) {
        allEdges.push({
          id: `e-${stage.execution_order[i]}-${stage.execution_order[i + 1]}`,
          source: stage.execution_order[i],
          sourceHandle: 'func-out',
          target: stage.execution_order[i + 1],
          targetHandle: 'func-in',
          type: 'default', // Bezier curve (smooth)
          animated: true,
          markerEnd: {
            type: 'arrowclosed',
            width: 20,
            height: 20,
          },
          style: {
            strokeWidth: 6,
          },
        });
      }

      // Collect all parameter nodes (explicit + auto-created)
      const allParamNodes = [...explicitParamNodes, ...autoCreatedParamNodes];

      // Apply staggered layout to position nodes (now includes Init node)
      const { nodes: layoutedNodes } = createStaggeredLayout(
        functionNodes,
        allParamNodes,
        allEdges,
        executionOrder,
        initNode  // Pass Init node to layout
      );

      newStageNodes[stageName] = layoutedNodes;
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

    /**
     * Find all nodes reachable from Init node via graph traversal
     * Returns an ordered array of function node IDs based on BFS traversal
     */
    const findReachableNodes = (nodes, edges, stageName) => {
      const initNodeId = `init-${stageName}`;
      const initNode = nodes.find(n => n.id === initNodeId);
      if (!initNode) return [];

      // Build adjacency list from edges (following func-out -> func-in connections)
      const adjacency = {};
      edges.forEach(edge => {
        if (edge.sourceHandle === 'func-out' || edge.sourceHandle === 'init-out') {
          if (!adjacency[edge.source]) adjacency[edge.source] = [];
          adjacency[edge.source].push(edge.target);
        }
      });

      // BFS from Init node to find reachable nodes in order
      const visited = new Set();
      const executionOrder = [];
      const queue = [initNodeId];
      visited.add(initNodeId);

      while (queue.length > 0) {
        const current = queue.shift();
        const neighbors = adjacency[current] || [];

        for (const neighbor of neighbors) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            // Only add function nodes to execution order (not Init)
            const node = nodes.find(n => n.id === neighbor);
            if (node && node.type === 'workflowFunction') {
              executionOrder.push(neighbor);
            }
            queue.push(neighbor);
          }
        }
      }

      return executionOrder;
    };

    // Convert React Flow nodes back to workflow functions and parameter nodes
    const stages = {};
    Object.keys(workflow.stages).forEach((stageName) => {
      const nodes = stageNodes[stageName] || [];
      const edges = stageEdges[stageName] || [];

      // Find execution order by traversing from Init node
      // Only nodes connected to Init (directly or indirectly) will be in execution_order
      const execution_order = findReachableNodes(nodes, edges, stageName);

      // Separate function nodes and parameter nodes
      const functionNodes = nodes.filter(n => n.type === 'workflowFunction');
      const parameterNodes = nodes.filter(n => n.type === 'parameterNode');

      // Export ALL function nodes (connected or not) - they stay in the canvas
      // Only connected ones will be in execution_order
      const functions = functionNodes.map((node) => {
        // Find parameter connections for this function
        const parameterConnections = edges
          .filter(e => e.target === node.id && e.targetHandle?.startsWith('params'))
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
          step_count: node.data.stepCount || 1,
          parameter_nodes: parameterConnections,
        };
      });

      // Export ALL parameter nodes
      const parameters = parameterNodes.map((node) => ({
        id: node.id,
        label: node.data.label || 'Parameters',
        parameters: node.data.parameters || {},
        position: node.position,
      }));

      stages[stageName] = {
        enabled: workflow.stages[stageName]?.enabled !== false,
        steps: workflow.stages[stageName]?.steps || 1,
        functions,
        parameters,
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

