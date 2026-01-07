import { create } from 'zustand';
import { createStaggeredLayout } from '../utils/layoutUtils';

/**
 * Workflow Store - Manages the entire workflow state
 * Compatible with MicroC workflow JSON format
 */
const useWorkflowStore = create((set, get) => ({
  // Workflow metadata
  workflow: {
    version: '2.0',  // Default to new sub-workflow system
    name: 'Untitled Workflow',
    description: '',
    metadata: {
      author: '',
      created: new Date().toISOString().split('T')[0],
    },
    // Legacy stages (v1.0)
    stages: {
	      initialization: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      macrostep: { enabled: false, steps: 1, functions: [], execution_order: [] },
	      intracellular: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      microenvironment: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      intercellular: { enabled: true, steps: 1, functions: [], execution_order: [] },
	      finalization: { enabled: true, steps: 1, functions: [], execution_order: [] },
	    },
    // New sub-workflows (v2.0)
    subworkflows: {
      main: {
        description: 'Main workflow entry point',
        enabled: true,
        deletable: false,
        controller: {
          id: 'controller-main',
          type: 'controller',
          label: 'MAIN CONTROLLER',
          position: { x: 100, y: 100 },
          number_of_steps: 1
        },
        functions: [],
        subworkflow_calls: [],
        parameters: [],
        execution_order: [],
        input_parameters: []
      }
    }
  },

  // Current active stage/subworkflow
  currentStage: 'main',  // For v2.0, this is the current sub-workflow name

  // React Flow nodes and edges for each stage (v1.0) or subworkflow (v2.0)
  stageNodes: {
    // Legacy stages
    initialization: [],
    macrostep: [],
    intracellular: [],
    microenvironment: [],
    intercellular: [],
    finalization: [],
    // Default main subworkflow
    main: []
  },

  stageEdges: {
    // Legacy stages
    initialization: [],
    macrostep: [],
    intracellular: [],
    microenvironment: [],
    intercellular: [],
    finalization: [],
    // Default main subworkflow
    main: []
  },

  // Simulation logs (persistent across tab changes)
  simulationLogs: [],

  // Call stack logs (for sub-workflow debugging)
  callStackLogs: [],

  // Actions
  setCurrentStage: (stage) => set({ currentStage: stage }),

  setWorkflowMetadata: (metadata) =>
    set((state) => ({
      workflow: {
        ...state.workflow,
        ...metadata,
      },
    })),

  // Simulation log actions
  addSimulationLog: (type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    set((state) => ({
      simulationLogs: [...state.simulationLogs, { type, message, timestamp }],
    }));
  },

  clearSimulationLogs: () => set({ simulationLogs: [] }),

  // Call stack log actions
  addCallStackLog: (entry) => {
    set((state) => ({
      callStackLogs: [...state.callStackLogs, entry],
    }));
  },

  clearCallStackLogs: () => set({ callStackLogs: [] }),

  // Sub-workflow management actions (v2.0)
  addSubWorkflow: (name, description = '') => {
    set((state) => {
      if (state.workflow.version !== '2.0') {
        console.warn('[STORE] Cannot add sub-workflow in v1.0 workflow');
        return state;
      }

      // Check if name already exists
      if (state.workflow.subworkflows[name]) {
        console.warn(`[STORE] Sub-workflow '${name}' already exists`);
        return state;
      }

      // Validate name
      if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) {
        console.error(`[STORE] Invalid sub-workflow name: ${name}`);
        return state;
      }

      return {
        workflow: {
          ...state.workflow,
          subworkflows: {
            ...state.workflow.subworkflows,
            [name]: {
              description,
              enabled: true,
              deletable: true,
              controller: {
                id: `controller-${name}`,
                type: 'controller',
                label: `${name.toUpperCase()} CONTROLLER`,
                position: { x: 100, y: 100 },
                number_of_steps: 1
              },
              functions: [],
              subworkflow_calls: [],
              parameters: [],
              execution_order: [],
              input_parameters: []
            }
          }
        },
        stageNodes: {
          ...state.stageNodes,
          [name]: [{
            id: `controller-${name}`,
            type: 'controller',
            position: { x: 100, y: 100 },
            data: {
              label: `${name.toUpperCase()} CONTROLLER`,
              number_of_steps: 1
            }
          }]
        },
        stageEdges: {
          ...state.stageEdges,
          [name]: []
        }
      };
    });
  },

  deleteSubWorkflow: (name) => {
    set((state) => {
      if (state.workflow.version !== '2.0') {
        console.warn('[STORE] Cannot delete sub-workflow in v1.0 workflow');
        return state;
      }

      // Cannot delete main workflow
      if (name === 'main') {
        console.error('[STORE] Cannot delete main workflow');
        return state;
      }

      // Check if deletable
      const subworkflow = state.workflow.subworkflows[name];
      if (!subworkflow || !subworkflow.deletable) {
        console.error(`[STORE] Sub-workflow '${name}' is not deletable`);
        return state;
      }

      // Remove from subworkflows
      const { [name]: removed, ...remainingSubworkflows } = state.workflow.subworkflows;

      // Remove from nodes and edges
      const { [name]: removedNodes, ...remainingNodes } = state.stageNodes;
      const { [name]: removedEdges, ...remainingEdges } = state.stageEdges;

      // Switch to main if current stage is being deleted
      const newCurrentStage = state.currentStage === name ? 'main' : state.currentStage;

      return {
        workflow: {
          ...state.workflow,
          subworkflows: remainingSubworkflows
        },
        stageNodes: remainingNodes,
        stageEdges: remainingEdges,
        currentStage: newCurrentStage
      };
    });
  },

  renameSubWorkflow: (oldName, newName) => {
    set((state) => {
      if (state.workflow.version !== '2.0') {
        console.warn('[STORE] Cannot rename sub-workflow in v1.0 workflow');
        return state;
      }

      // Cannot rename main workflow
      if (oldName === 'main') {
        console.error('[STORE] Cannot rename main workflow');
        return state;
      }

      // Validate new name
      if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(newName)) {
        console.error(`[STORE] Invalid sub-workflow name: ${newName}`);
        return state;
      }

      // Check if new name already exists
      if (state.workflow.subworkflows[newName]) {
        console.error(`[STORE] Sub-workflow '${newName}' already exists`);
        return state;
      }

      // Get the subworkflow
      const subworkflow = state.workflow.subworkflows[oldName];
      if (!subworkflow) {
        console.error(`[STORE] Sub-workflow '${oldName}' not found`);
        return state;
      }

      // Create new subworkflows object with renamed key
      const newSubworkflows = {};
      Object.keys(state.workflow.subworkflows).forEach(key => {
        if (key === oldName) {
          newSubworkflows[newName] = {
            ...subworkflow,
            // Update controller label
            controller: {
              ...subworkflow.controller,
              id: `controller-${newName}`,
              label: `${newName.toUpperCase()} CONTROLLER`
            }
          };
        } else {
          newSubworkflows[key] = state.workflow.subworkflows[key];
        }
      });

      // Rename in nodes and edges
      const newStageNodes = {};
      const newStageEdges = {};
      Object.keys(state.stageNodes).forEach(key => {
        if (key === oldName) {
          newStageNodes[newName] = state.stageNodes[key];
        } else {
          newStageNodes[key] = state.stageNodes[key];
        }
      });
      Object.keys(state.stageEdges).forEach(key => {
        if (key === oldName) {
          newStageEdges[newName] = state.stageEdges[key];
        } else {
          newStageEdges[key] = state.stageEdges[key];
        }
      });

      // Update current stage if needed
      const newCurrentStage = state.currentStage === oldName ? newName : state.currentStage;

      return {
        workflow: {
          ...state.workflow,
          subworkflows: newSubworkflows
        },
        stageNodes: newStageNodes,
        stageEdges: newStageEdges,
        currentStage: newCurrentStage
      };
    });
  },

  updateSubWorkflowDescription: (name, description) => {
    set((state) => {
      if (state.workflow.version !== '2.0') {
        return state;
      }

      if (!state.workflow.subworkflows[name]) {
        return state;
      }

      return {
        workflow: {
          ...state.workflow,
          subworkflows: {
            ...state.workflow.subworkflows,
            [name]: {
              ...state.workflow.subworkflows[name],
              description
            }
          }
        }
      };
    });
  },

  // Load workflow from JSON - LOADS ALL STAGES/SUBWORKFLOWS
  loadWorkflow: (workflowJson) => {
    const version = workflowJson.version || '1.0';

    if (version === '2.0') {
      // Load v2.0 sub-workflow format
      get()._loadWorkflowV2(workflowJson);
    } else {
      // Load v1.0 stage format
      get()._loadWorkflowV1(workflowJson);
    }
  },

  // Load v1.0 stage-based workflow
  _loadWorkflowV1: (workflowJson) => {
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
      // Generate label based on stage name (e.g., "Initialization Controller")
      const capitalizedStage = stageName.charAt(0).toUpperCase() + stageName.slice(1);
      const initNode = {
        id: initNodeId,
        type: 'initNode',
        position: { x: 0, y: 0 }, // Will be set by layout
        data: {
          label: `${capitalizedStage} Controller`,
          // Set the number of steps from the stage (for all stages)
          numberOfSteps: stage.steps || 1,
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

      // Create edge from controller parameter node to controller (if specified)
      if (stageName === 'macrostep' && stage.controller_parameter_node) {
        allEdges.push({
          id: `e-controller-param-${stage.controller_parameter_node}-${initNodeId}`,
          source: stage.controller_parameter_node,
          sourceHandle: 'params',
          target: initNodeId,
          targetHandle: 'steps-param',
          type: 'default',
          animated: false,
          markerEnd: {
            type: 'arrowclosed',
            width: 10,
            height: 10,
            color: '#3b82f6', // Blue arrow tip
          },
          style: {
            strokeWidth: 4,
            stroke: '#3b82f6', // Blue edge
          },
        });
      }

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
                width: 10,
                height: 10,
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
            width: 10,
            height: 10,
            color: '#dc2626', // Red arrow tip to match Init node
          },
          style: {
            strokeWidth: 6,
            stroke: '#dc2626', // Red edge from Init
          },
        });
      }

      // Create function flow edges - prefer function_edges if available, otherwise use execution_order
      if (stage.function_edges && Array.isArray(stage.function_edges) && stage.function_edges.length > 0) {
        // Use preserved function edges (maintains connections even if disconnected from controller)
        stage.function_edges.forEach((edge) => {
          allEdges.push({
            id: `e-${edge.source}-${edge.target}`,
            source: edge.source,
            sourceHandle: 'func-out',
            target: edge.target,
            targetHandle: 'func-in',
            type: 'default',
            animated: true,
            markerEnd: {
              type: 'arrowclosed',
              width: 10,
              height: 10,
            },
            style: {
              strokeWidth: 6,
            },
          });
        });
      } else {
        // Fallback: Create function flow edges based on execution order (legacy behavior)
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
              width: 10,
              height: 10,
            },
            style: {
              strokeWidth: 6,
            },
          });
        }
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

  // Load v2.0 sub-workflow-based workflow
  _loadWorkflowV2: (workflowJson) => {
    const { subworkflows } = workflowJson;
    if (!subworkflows) {
      console.error('[STORE] No subworkflows found in v2.0 workflow');
      return;
    }

    const newStageNodes = {};
    const newStageEdges = {};

    // Process each sub-workflow
    Object.keys(subworkflows).forEach((subworkflowName) => {
      const subworkflow = subworkflows[subworkflowName];
      const allEdges = [];
      const createdParamNodeIds = new Set();

      // Build execution order for layout
      const executionOrder = subworkflow.execution_order || [];

      // Create controller node
      const controller = subworkflow.controller;
      const controllerNode = controller ? {
        id: controller.id,
        type: 'controller',
        position: controller.position || { x: 100, y: 100 },
        data: {
          label: controller.label || `${subworkflowName.toUpperCase()} CONTROLLER`,
          number_of_steps: controller.number_of_steps || 1
        },
        deletable: false
      } : null;

      // Create parameter nodes
      const explicitParamNodes = (subworkflow.parameters || []).map((param) => ({
        id: param.id,
        type: 'parameterNode',
        position: param.position || { x: 0, y: 0 },
        data: {
          label: param.label || 'Parameters',
          parameters: param.parameters || {},
          onEdit: () => {}
        }
      }));
      explicitParamNodes.forEach(node => createdParamNodeIds.add(node.id));

      // Create function nodes
      const functionNodes = (subworkflow.functions || []).map((func) => ({
        id: func.id,
        type: 'workflowFunction',
        position: func.position || { x: 0, y: 0 },
        data: {
          label: func.function_name,
          functionName: func.function_name,
          parameters: func.parameters || {},
          enabled: func.enabled !== false,
          description: func.description || '',
          functionFile: func.function_file || func.parameters?.function_file || '',
          customName: func.custom_name || '',
          stepCount: func.step_count || 1,
          onEdit: () => {}
        }
      }));

      // Create sub-workflow call nodes
      const subworkflowCallNodes = (subworkflow.subworkflow_calls || []).map((call) => ({
        id: call.id,
        type: 'subworkflowCall',
        position: call.position || { x: 0, y: 0 },
        data: {
          label: call.subworkflow_name,
          subworkflowName: call.subworkflow_name,
          iterations: call.iterations || 1,
          parameters: call.parameters || {},
          enabled: call.enabled !== false,
          description: call.description || '',
          onEdit: () => {}
        }
      }));

      // Create parameter edges
      [...(subworkflow.functions || []), ...(subworkflow.subworkflow_calls || [])].forEach((node) => {
        if (node.parameter_nodes && node.parameter_nodes.length > 0) {
          node.parameter_nodes.forEach((paramNodeId) => {
            allEdges.push({
              id: `e-param-${paramNodeId}-${node.id}`,
              source: paramNodeId,
              sourceHandle: 'params',
              target: node.id,
              targetHandle: 'params',
              type: 'default',
              animated: false,
              style: {
                stroke: '#3b82f6',
                strokeWidth: 2,
                strokeDasharray: '5,5'
              }
            });
          });
        }
      });

      // Create execution flow edges based on execution order
      if (controllerNode && executionOrder.length > 0) {
        // Edge from controller to first node
        allEdges.push({
          id: `e-${controllerNode.id}-${executionOrder[0]}`,
          source: controllerNode.id,
          sourceHandle: 'func-out',
          target: executionOrder[0],
          targetHandle: 'func-in',
          type: 'default',
          animated: true,
          markerEnd: {
            type: 'arrowclosed',
            width: 10,
            height: 10
          },
          style: {
            strokeWidth: 6
          }
        });

        // Edges between nodes in execution order
        for (let i = 0; i < executionOrder.length - 1; i++) {
          allEdges.push({
            id: `e-${executionOrder[i]}-${executionOrder[i + 1]}`,
            source: executionOrder[i],
            sourceHandle: 'func-out',
            target: executionOrder[i + 1],
            targetHandle: 'func-in',
            type: 'default',
            animated: true,
            markerEnd: {
              type: 'arrowclosed',
              width: 10,
              height: 10
            },
            style: {
              strokeWidth: 6
            }
          });
        }
      }

      // Collect all nodes
      const allNodes = [
        ...(controllerNode ? [controllerNode] : []),
        ...functionNodes,
        ...subworkflowCallNodes,
        ...explicitParamNodes
      ];

      newStageNodes[subworkflowName] = allNodes;
      newStageEdges[subworkflowName] = allEdges;
    });

    set((state) => ({
      workflow: {
        ...state.workflow,
        ...workflowJson,
        subworkflows: {
          ...subworkflows
        }
      },
      stageNodes: newStageNodes,
      stageEdges: newStageEdges,
      currentStage: 'main' // Always start with main
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

      // Export function-to-function edges (preserve connections even if disconnected from controller)
      const function_edges = edges
        .filter(e => e.sourceHandle === 'func-out' && e.targetHandle === 'func-in')
        .map(e => ({
          source: e.source,
          target: e.target,
        }));

      // Get the number of steps from the controller node
      let stageSteps = workflow.stages[stageName]?.steps || 1;
      let controllerParameterNode = null;

      const controllerNode = nodes.find(n => n.id === `init-${stageName}`);
      if (controllerNode) {
        // For macrostep stage, check if a parameter node is connected
        if (stageName === 'macrostep' && controllerNode.data.isStepsParameterConnected && controllerNode.data.connectedStepsValue !== undefined) {
          stageSteps = controllerNode.data.connectedStepsValue;

          // Find which parameter node is connected to the controller
          const controllerEdge = edges.find(
            e => e.targetHandle === 'steps-param' && e.target === `init-${stageName}`
          );
          if (controllerEdge) {
            controllerParameterNode = controllerEdge.source;
          }
        } else if (controllerNode.data.numberOfSteps) {
          // Use the controller's numberOfSteps value (for all stages)
          stageSteps = controllerNode.data.numberOfSteps;
        }
      }

      stages[stageName] = {
        enabled: workflow.stages[stageName]?.enabled !== false,
        steps: stageSteps,
        functions,
        parameters,
        execution_order,
        // Preserve function-to-function edges
        ...(function_edges.length > 0 && { function_edges }),
        // Add controller_parameter_node for macrostep stage if connected
        ...(stageName === 'macrostep' && controllerParameterNode && {
          controller_parameter_node: controllerParameterNode,
        }),
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

