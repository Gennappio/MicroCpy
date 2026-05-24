/**
 * Workflow Store - Manages the entire workflow state
 *
 * This store is composed of multiple slices for better maintainability:
 * - observabilitySlice: Node selection, cell selection, inspector, badge stats
 * - subworkflowSlice: Sub-workflow CRUD operations
 * - nodeActionsSlice: Node/function manipulation
 * - librarySlice: Function library management
 * - workflowIOSlice: Load/export/import workflows
 * - logSlice: Simulation and workflow logs
 *
 * Compatible with workflow JSON format v2.0
 */

import { create } from 'zustand';
import {
  createObservabilitySlice,
  createSubworkflowSlice,
  createNodeActionsSlice,
  createLibrarySlice,
  createWorkflowIOSlice,
  createLogSlice,
  createPlannerSlice,
  createAbmSlice,
} from './slices';
import { KINDS, SCHEDULER_NAME } from './subworkflowKinds';

/**
 * Workflow Store - Manages the entire workflow state
 * Compatible with workflow JSON format
 */
const useWorkflowStore = create((set, get) => ({
  // ===== Core Workflow State =====

  // Workflow metadata
  workflow: {
    version: '2.0',  // V2-only: no backward compatibility
    name: 'Untitled Workflow',
    description: '',
    metadata: {
      author: '',
      created: new Date().toISOString().split('T')[0],
      gui: {
        subworkflow_kinds: {
          [SCHEDULER_NAME]: KINDS.SCHEDULER,
        },
        function_libraries: [],
        agent_kinds: [],
        environment: { init_subworkflow: null, behavior_subworkflows: [] },
        scheduler: { subworkflow: SCHEDULER_NAME },
        processing: { behavior_subworkflows: [] },
        main_is_synthesized: false,
      }
    },
    subworkflows: {
      [SCHEDULER_NAME]: {
        description: 'Main simulation loop — order behaviors here',
        enabled: true,
        deletable: false,
        controller: {
          id: `controller-${SCHEDULER_NAME}`,
          type: 'initNode',
          label: 'SCHEDULER',
          position: { x: 100, y: 100 },
          number_of_steps: 100,
        },
        functions: [],
        subworkflow_calls: [],
        parameters: [],
        execution_order: [],
        input_parameters: [],
      },
    },
  },

  currentStage: SCHEDULER_NAME,

  currentMainTab: 'agents',

  stageNodes: {
    [SCHEDULER_NAME]: [],
  },

  stageEdges: {
    [SCHEDULER_NAME]: [],
  },

  // ===== Core Actions =====

  setCurrentStage: (stage) => set({ currentStage: stage }),

  setCurrentMainTab: (tab) => set({ currentMainTab: tab }),

  setWorkflowMetadata: (metadata) =>
    set((state) => ({
      workflow: {
        ...state.workflow,
        ...metadata,
      },
    })),

  // ===== Compose Slices =====

  // Observability: node selection, cell selection, inspector, badges
  ...createObservabilitySlice(set, get),

  // Subworkflow management: add, delete, rename, update description
  ...createSubworkflowSlice(set, get),

  // Node actions: add, remove, update, toggle enabled/verbose
  ...createNodeActionsSlice(set, get),

  // Library management: add, remove, get function libraries
  ...createLibrarySlice(set, get),

  // Workflow I/O: load, export, import workflows
  ...createWorkflowIOSlice(set, get),

  // Logs: simulation logs, workflow logs, call stack logs
  ...createLogSlice(set, get),

  // Planner: multiple parameter configurations
  ...createPlannerSlice(set, get),

  // ABM: agent kinds, environment, scheduler, processing
  ...createAbmSlice(set, get),
}));

export default useWorkflowStore;

