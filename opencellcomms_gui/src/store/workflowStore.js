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
import { SCHEDULER_NAME, INIT_SEQUENCE_NAME } from './subworkflowKinds';
import { computeSubworkflowKinds } from './computeSubworkflowKinds';

/**
 * Workflow Store - Manages the entire workflow state
 * Compatible with workflow JSON format
 */
// Phase 14B: subworkflow_kinds is derived from ABM metadata, not seeded.
const _defaultGuiMeta = {
  function_libraries: [],
  agent_kinds: [],
  resource_kinds: [],
  space: { subworkflow: null },
  environment: { init_subworkflow: null, behavior_subworkflows: [] },
  init_sequence: { subworkflow: INIT_SEQUENCE_NAME },
  scheduler: { subworkflow: SCHEDULER_NAME },
  processing: { behavior_subworkflows: [] },
  main_is_synthesized: false,
  user_functions: [],
};

const _makeEmptyControllerSubworkflow = (name, label, steps, description) => ({
  description,
  enabled: true,
  deletable: false,
  controller: {
    id: `controller-${name}`,
    type: 'initNode',
    label,
    position: { x: 100, y: 100 },
    number_of_steps: steps,
  },
  functions: [],
  subworkflow_calls: [],
  parameters: [],
  execution_order: [],
  input_parameters: [],
});

const _defaultSubworkflows = {
  [INIT_SEQUENCE_NAME]: _makeEmptyControllerSubworkflow(
    INIT_SEQUENCE_NAME,
    'INIT SEQUENCE',
    1,
    'Initialization order — drag init subworkflows here',
  ),
  [SCHEDULER_NAME]: _makeEmptyControllerSubworkflow(
    SCHEDULER_NAME,
    'SCHEDULER',
    1,
    'Main simulation loop — order behaviors here',
  ),
};

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
        ..._defaultGuiMeta,
        subworkflow_kinds: computeSubworkflowKinds({
          metadata: { gui: _defaultGuiMeta },
          subworkflows: _defaultSubworkflows,
        }),
      }
    },
    subworkflows: _defaultSubworkflows,
  },

  currentStage: SCHEDULER_NAME,

  currentMainTab: 'agents',

  stageNodes: {
    [INIT_SEQUENCE_NAME]: [],
    [SCHEDULER_NAME]: [],
  },

  stageEdges: {
    [INIT_SEQUENCE_NAME]: [],
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

