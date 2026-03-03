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
} from './slices';

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
        // Subworkflow kind classification: 'composer' | 'subworkflow'
        subworkflow_kinds: {
          main: 'composer'  // main is always a composer
        },
        // Function libraries (Phase 5)
        function_libraries: []
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
  currentStage: 'main',

  // Current main tab: 'composers' | 'subworkflows' | 'planner' | 'results'
  currentMainTab: 'composers',

  // React Flow nodes and edges for each subworkflow
  stageNodes: {
    main: []
  },

  stageEdges: {
    main: []
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
}));

export default useWorkflowStore;

