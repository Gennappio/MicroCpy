/**
 * Node Actions Slice
 *
 * Manages node/function manipulation operations: add, remove, update,
 * toggle enabled/verbose states, and stage nodes/edges management.
 */

/**
 * Creates the node actions slice
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Node action functions
 */
export const createNodeActionsSlice = (set, get) => ({
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
        verbose: false,
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

  /**
   * Toggle verbose logging for a node.
   * When toggling a subworkflow call node, propagates the verbose setting
   * to all nodes within that subworkflow (hierarchically).
   */
  toggleNodeVerbose: (nodeId, subworkflowName = null) =>
    set((state) => {
      // First, find the node being toggled
      let toggledNode = null;
      Object.keys(state.stageNodes).forEach((stageName) => {
        const node = state.stageNodes[stageName].find(n => n.id === nodeId);
        if (node) {
          toggledNode = node;
        }
      });

      if (!toggledNode) return state;

      const newVerbose = !toggledNode.data.verbose;
      const newStageNodes = {};

      // Toggle the node itself
      Object.keys(state.stageNodes).forEach((stageName) => {
        newStageNodes[stageName] = state.stageNodes[stageName].map((node) => {
          if (node.id === nodeId) {
            return {
              ...node,
              data: { ...node.data, verbose: newVerbose }
            };
          }
          return node;
        });
      });

      // If this is a subworkflow call, propagate to all nodes in that subworkflow
      if (subworkflowName && newStageNodes[subworkflowName]) {
        newStageNodes[subworkflowName] = newStageNodes[subworkflowName].map((node) => {
          if (node.type === 'workflowFunction' || node.type === 'subworkflowCall') {
            return {
              ...node,
              data: { ...node.data, verbose: newVerbose }
            };
          }
          return node;
        });

        // Also propagate to nested subworkflows (recursively)
        const propagateToSubworkflow = (swName, verboseValue) => {
          if (!newStageNodes[swName]) return;

          newStageNodes[swName] = newStageNodes[swName].map((node) => {
            if (node.type === 'workflowFunction' || node.type === 'subworkflowCall') {
              if (node.type === 'subworkflowCall' && node.data.subworkflowName) {
                propagateToSubworkflow(node.data.subworkflowName, verboseValue);
              }
              return {
                ...node,
                data: { ...node.data, verbose: verboseValue }
              };
            }
            return node;
          });
        };

        (newStageNodes[subworkflowName] || []).forEach((node) => {
          if (node.type === 'subworkflowCall' && node.data.subworkflowName) {
            propagateToSubworkflow(node.data.subworkflowName, newVerbose);
          }
        });
      }

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
});

