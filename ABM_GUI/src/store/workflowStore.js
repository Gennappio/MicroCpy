import { create } from 'zustand';

/**
 * Workflow Store - Manages the entire workflow state
 * Compatible with MicroC workflow JSON format
 */
const useWorkflowStore = create((set, get) => ({
  // Workflow metadata
  workflow: {
    version: '2.0',  // V2-only: no backward compatibility
    name: 'Untitled Workflow',
    description: '',
    metadata: {
      author: '',
      created: new Date().toISOString().split('T')[0],
      gui: {
        // Subworkflow kind classification: 'composer' | 'subworkflow'
        subworkflow_kinds: {
          main: 'composer'  // main is always a composer
        }
      }
    },
    // V2.0 sub-workflows
    subworkflows: {
      main: {
        description: 'Main workflow entry point',
        enabled: true,
        deletable: false,
        controller: {
          id: 'controller-main',
          type: 'initNode',
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

  // Current active subworkflow
  currentStage: 'main',  // Current sub-workflow name (keeping 'currentStage' for compatibility)

  // Current main tab: 'composers' | 'subworkflows'
  currentMainTab: 'composers',

  // React Flow nodes and edges for each subworkflow
  stageNodes: {
    main: []  // Default main composer
  },

  stageEdges: {
    main: []  // Default main composer
  },

  // Simulation logs (persistent across tab changes)
  simulationLogs: [],

  // Call stack logs (for sub-workflow debugging)
  callStackLogs: [],

  // Actions
  setCurrentStage: (stage) => set({ currentStage: stage }),

  setCurrentMainTab: (tab) => set({ currentMainTab: tab }),

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
  addSubWorkflow: (name, description = '', kind = null) => {
    set((state) => {
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

      // Determine kind: use provided kind, or infer from currentMainTab
      const subworkflowKind = kind || (state.currentMainTab === 'composers' ? 'composer' : 'subworkflow');

      return {
        workflow: {
          ...state.workflow,
          metadata: {
            ...state.workflow.metadata,
            gui: {
              ...state.workflow.metadata.gui,
              subworkflow_kinds: {
                ...state.workflow.metadata.gui.subworkflow_kinds,
                [name]: subworkflowKind
              }
            }
          },
          subworkflows: {
            ...state.workflow.subworkflows,
            [name]: {
              description,
              enabled: true,
              deletable: true,
              controller: {
                id: `controller-${name}`,
                type: 'initNode',
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
            type: 'initNode',
            position: { x: 100, y: 100 },
            data: {
              label: `${name.toUpperCase()} CONTROLLER`,
              numberOfSteps: 1
            },
            deletable: false
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

      // Remove from subworkflow_kinds
      const { [name]: removedKind, ...remainingKinds } = state.workflow.metadata.gui.subworkflow_kinds;

      // Remove from nodes and edges
      const { [name]: removedNodes, ...remainingNodes } = state.stageNodes;
      const { [name]: removedEdges, ...remainingEdges } = state.stageEdges;

      // Switch to main if current stage is being deleted
      const newCurrentStage = state.currentStage === name ? 'main' : state.currentStage;

      return {
        workflow: {
          ...state.workflow,
          metadata: {
            ...state.workflow.metadata,
            gui: {
              ...state.workflow.metadata.gui,
              subworkflow_kinds: remainingKinds
            }
          },
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

      // Get the kind
      const kind = state.workflow.metadata.gui.subworkflow_kinds[oldName];

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

      // Create new subworkflow_kinds with renamed key
      const newSubworkflowKinds = {};
      Object.keys(state.workflow.metadata.gui.subworkflow_kinds).forEach(key => {
        if (key === oldName) {
          newSubworkflowKinds[newName] = kind;
        } else {
          newSubworkflowKinds[key] = state.workflow.metadata.gui.subworkflow_kinds[key];
        }
      });

      // Update any SubWorkflowCall nodes that reference the old name
      const newStageNodes = {};
      Object.keys(state.stageNodes).forEach(stageName => {
        if (stageName === oldName) {
          newStageNodes[newName] = state.stageNodes[stageName];
        } else {
          // Update subworkflow call nodes that reference oldName
          newStageNodes[stageName] = state.stageNodes[stageName].map(node => {
            if (node.type === 'subworkflowCall' && node.data.subworkflowName === oldName) {
              return {
                ...node,
                data: {
                  ...node.data,
                  subworkflowName: newName,
                  label: newName
                }
              };
            }
            return node;
          });
        }
      });

      const newStageEdges = {};
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
          metadata: {
            ...state.workflow.metadata,
            gui: {
              ...state.workflow.metadata.gui,
              subworkflow_kinds: newSubworkflowKinds
            }
          },
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

  // Load workflow from JSON - V2-ONLY (no backward compatibility)
  loadWorkflow: (workflowJson) => {
    const version = workflowJson.version;

    // Strict v2-only policy
    if (version !== '2.0') {
      const errorMsg = `Unsupported workflow version: ${version || 'undefined'}. Only version 2.0 is supported.`;
      console.error(`[STORE] ${errorMsg}`);
      alert(errorMsg);
      throw new Error(errorMsg);
    }

    // Load v2.0 sub-workflow format
    get()._loadWorkflowV2(workflowJson);
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
        type: 'initNode',
        position: controller.position || { x: 100, y: 100 },
        data: {
          label: controller.label || `${subworkflowName.toUpperCase()} CONTROLLER`,
          numberOfSteps: controller.number_of_steps || 1
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
          results: call.results || '',
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

    // Load or infer subworkflow_kinds
    const loadedKinds = workflowJson.metadata?.gui?.subworkflow_kinds || {};
    const subworkflowKinds = {};

    Object.keys(subworkflows).forEach(name => {
      if (loadedKinds[name]) {
        // Use loaded kind
        subworkflowKinds[name] = loadedKinds[name];
      } else {
        // Infer: main is composer, others are subworkflow
        subworkflowKinds[name] = name === 'main' ? 'composer' : 'subworkflow';
      }
    });

    set((state) => ({
      workflow: {
        ...state.workflow,
        ...workflowJson,
        metadata: {
          ...workflowJson.metadata,
          gui: {
            ...workflowJson.metadata?.gui,
            subworkflow_kinds: subworkflowKinds
          }
        },
        subworkflows: {
          ...subworkflows
        }
      },
      stageNodes: newStageNodes,
      stageEdges: newStageEdges,
      currentStage: 'main' // Always start with main
    }));
  },

  // Export workflow to JSON (V2-only)
  exportWorkflow: () => {
    const state = get();
    const { workflow, stageNodes, stageEdges } = state;

    // Validate call hierarchy before export
    const validationErrors = [];
    Object.keys(workflow.subworkflows).forEach((subworkflowName) => {
      const nodes = stageNodes[subworkflowName] || [];
      const subworkflowKind = workflow.metadata?.gui?.subworkflow_kinds?.[subworkflowName] ||
                             (subworkflowName === 'main' ? 'composer' : 'subworkflow');

      // Check all subworkflow call nodes
      const callNodes = nodes.filter(n => n.type === 'subworkflowCall');
      callNodes.forEach((callNode) => {
        const targetName = callNode.data.subworkflowName;
        const targetKind = workflow.metadata?.gui?.subworkflow_kinds?.[targetName] ||
                          (targetName === 'main' ? 'composer' : 'subworkflow');

        // Sub-workflows cannot call composers
        if (subworkflowKind === 'subworkflow' && targetKind === 'composer') {
          validationErrors.push(
            `Invalid call in '${subworkflowName}': Sub-workflows cannot call composers (attempted to call '${targetName}')`
          );
        }
      });
    });

    if (validationErrors.length > 0) {
      const errorMessage = 'Call hierarchy validation failed:\n\n' + validationErrors.join('\n');
      console.error('[EXPORT] Validation errors:', validationErrors);
      alert(errorMessage);
      throw new Error(errorMessage);
    }

    /**
     * Find all nodes reachable from controller node via graph traversal
     * Returns an ordered array of node IDs (functions and subworkflow calls) based on BFS traversal
     */
    const findReachableNodes = (nodes, edges, subworkflowName) => {
      const controllerNodeId = `controller-${subworkflowName}`;
      const controllerNode = nodes.find(n => n.id === controllerNodeId);
      if (!controllerNode) return [];

      // Build adjacency list from edges (following func-out -> func-in connections)
      const adjacency = {};
      edges.forEach(edge => {
        if (edge.sourceHandle === 'func-out' || edge.sourceHandle === 'init-out') {
          if (!adjacency[edge.source]) adjacency[edge.source] = [];
          adjacency[edge.source].push(edge.target);
        }
      });

      // BFS from controller node to find reachable nodes in order
      const visited = new Set();
      const executionOrder = [];
      const queue = [controllerNodeId];
      visited.add(controllerNodeId);

      while (queue.length > 0) {
        const current = queue.shift();
        const neighbors = adjacency[current] || [];

        for (const neighbor of neighbors) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            // Add function nodes and subworkflow call nodes to execution order
            const node = nodes.find(n => n.id === neighbor);
            if (node && (node.type === 'workflowFunction' || node.type === 'subworkflowCall')) {
              executionOrder.push(neighbor);
            }
            queue.push(neighbor);
          }
        }
      }

      return executionOrder;
    };

    // Convert React Flow nodes back to subworkflows
    const subworkflows = {};
    Object.keys(workflow.subworkflows).forEach((subworkflowName) => {
      const nodes = stageNodes[subworkflowName] || [];
      const edges = stageEdges[subworkflowName] || [];

      // Find execution order by traversing from controller node
      const execution_order = findReachableNodes(nodes, edges, subworkflowName);

      // Separate node types
      const functionNodes = nodes.filter(n => n.type === 'workflowFunction');
      const subworkflowCallNodes = nodes.filter(n => n.type === 'subworkflowCall');
      const parameterNodes = nodes.filter(n => n.type === 'parameterNode');
      const controllerNode = nodes.find(n => n.id === `controller-${subworkflowName}`);

      // Export ALL function nodes
      const functions = functionNodes.map((node) => {
        // Find parameter connections for this function
        const parameterConnections = edges
          .filter(e => e.target === node.id && e.targetHandle?.startsWith('params'))
          .map(e => e.source);

        return {
          id: node.id,
          function_name: node.data.functionName,
          function_file: node.data.functionFile || '',
          parameters: node.data.parameters || {},
          enabled: node.data.enabled !== false,
          position: node.position,
          description: node.data.description || '',
          custom_name: node.data.customName || '',
          step_count: node.data.stepCount || 1,
          parameter_nodes: parameterConnections,
        };
      });

      // Export ALL subworkflow call nodes
      const subworkflow_calls = subworkflowCallNodes.map((node) => {
        // Find parameter connections for this call
        const parameterConnections = edges
          .filter(e => e.target === node.id && e.targetHandle?.startsWith('params'))
          .map(e => e.source);

        const exportedCall = {
          id: node.id,
          type: 'subworkflow_call',
          subworkflow_name: node.data.subworkflowName,
          iterations: node.data.iterations || 1,
          parameters: node.data.parameters || {},
          enabled: node.data.enabled !== false,
          position: node.position,
          description: node.data.description || '',
          parameter_nodes: parameterConnections,
          context_mapping: {} // TODO: implement context_mapping UI
        };

        // Only include results field if it's not empty
        if (node.data.results && node.data.results.trim() !== '') {
          exportedCall.results = node.data.results;
        }

        return exportedCall;
      });

      // Export ALL parameter nodes
      const parameters = parameterNodes.map((node) => ({
        id: node.id,
        label: node.data.label || 'Parameters',
        parameters: node.data.parameters || {},
        position: node.position,
      }));

      // Export controller
      const controller = controllerNode ? {
        id: controllerNode.id,
        type: 'controller',
        label: controllerNode.data.label || `${subworkflowName.toUpperCase()} CONTROLLER`,
        position: controllerNode.position,
        number_of_steps: controllerNode.data.numberOfSteps || 1
      } : null;

      subworkflows[subworkflowName] = {
        description: workflow.subworkflows[subworkflowName]?.description || '',
        enabled: workflow.subworkflows[subworkflowName]?.enabled !== false,
        deletable: workflow.subworkflows[subworkflowName]?.deletable !== false,
        controller,
        functions,
        subworkflow_calls,
        parameters,
        execution_order,
        input_parameters: workflow.subworkflows[subworkflowName]?.input_parameters || []
      };
    });

    return {
      version: '2.0',
      name: workflow.name,
      description: workflow.description,
      metadata: workflow.metadata,
      subworkflows,
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

  // Clear all workflow data
  clearWorkflow: () =>
    set({
      workflow: {
        version: '2.0',
        name: 'Untitled Workflow',
        description: '',
        metadata: {
          author: '',
          created: new Date().toISOString().split('T')[0],
          gui: {
            subworkflow_kinds: {
              main: 'composer'
            }
          }
        },
        subworkflows: {
          main: {
            description: 'Main composer workflow',
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
      currentStage: 'main',
      stageNodes: {
        main: [{
          id: 'controller-main',
          type: 'controllerNode',
          position: { x: 100, y: 100 },
          data: {
            label: 'MAIN CONTROLLER',
            numberOfSteps: 1
          },
          deletable: false
        }]
      },
      stageEdges: {
        main: []
      },
    }),
}));

export default useWorkflowStore;

