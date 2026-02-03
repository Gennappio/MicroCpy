/**
 * Subworkflow Slice
 *
 * Manages sub-workflow CRUD operations: add, delete, rename,
 * and description updates.
 */

/**
 * Creates the subworkflow management slice
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Subworkflow management actions
 */
export const createSubworkflowSlice = (set, get) => ({
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
});

