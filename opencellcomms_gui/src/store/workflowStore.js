import { create } from 'zustand';
import { validateWorkflow } from '../utils/workflowValidation';

/**
 * Path utilities for Phase 6: Path Handling
 */
const pathUtils = {
  /**
   * Make a path relative to a base directory
   * @param {string} absolutePath - The absolute path to convert
   * @param {string} basePath - The base directory path
   * @returns {string} Relative path
   */
  makeRelative: (absolutePath, basePath) => {
    if (!absolutePath || !basePath) return absolutePath;

    // Normalize paths (remove trailing slashes)
    const normAbsolute = absolutePath.replace(/\\/g, '/').replace(/\/$/, '');
    const normBase = basePath.replace(/\\/g, '/').replace(/\/$/, '');

    // Split into parts
    const absoluteParts = normAbsolute.split('/');
    const baseParts = normBase.split('/');

    // Find common prefix
    let commonLength = 0;
    while (
      commonLength < absoluteParts.length &&
      commonLength < baseParts.length &&
      absoluteParts[commonLength] === baseParts[commonLength]
    ) {
      commonLength++;
    }

    // Build relative path
    const upLevels = baseParts.length - commonLength;
    const downPath = absoluteParts.slice(commonLength);

    const relativeParts = [];
    for (let i = 0; i < upLevels; i++) {
      relativeParts.push('..');
    }
    relativeParts.push(...downPath);

    return relativeParts.join('/');
  },

  /**
   * Resolve a relative path against a base directory
   * @param {string} relativePath - The relative path to resolve
   * @param {string} basePath - The base directory path
   * @returns {string} Absolute path
   */
  resolve: (relativePath, basePath) => {
    if (!relativePath || !basePath) return relativePath;

    // If path is already absolute, return as-is
    if (relativePath.startsWith('/') || /^[A-Za-z]:/.test(relativePath)) {
      return relativePath;
    }

    // Normalize base path
    const normBase = basePath.replace(/\\/g, '/').replace(/\/$/, '');

    // Split paths
    const baseParts = normBase.split('/');
    const relativeParts = relativePath.split('/');

    // Process relative parts
    const resultParts = [...baseParts];
    for (const part of relativeParts) {
      if (part === '..') {
        resultParts.pop();
      } else if (part !== '.' && part !== '') {
        resultParts.push(part);
      }
    }

    return resultParts.join('/');
  },

  /**
   * Get directory path from file path
   * @param {string} filePath - Full file path
   * @returns {string} Directory path
   */
  dirname: (filePath) => {
    if (!filePath) return '';
    const normalized = filePath.replace(/\\/g, '/');
    const lastSlash = normalized.lastIndexOf('/');
    return lastSlash >= 0 ? normalized.substring(0, lastSlash) : '';
  }
};

/**
 * Workflow Store - Manages the entire workflow state
 * Compatible with workflow JSON format
 */
const useWorkflowStore = create((set, get) => ({
  // Current workflow file path (for relative path resolution)
  workflowFilePath: null,
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
        // Array of library objects: { path: string, functions: { [funcName]: 'overwrite' | 'variant' } }
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

  // Per-workflow logs (for integrated console)
  workflowLogs: {},

  // Call stack logs (for sub-workflow debugging)
  callStackLogs: [],

  // ===== NodeObservability: Ephemeral UI State =====

  /**
   * Selected node ID per subworkflow stage (ephemeral, UI-only).
   * Lifted from WorkflowCanvas local state so other panels can access it.
   * Shape: { [stageName]: nodeId | null }
   */
  selectedNodeByStage: {},

  /**
   * Ephemeral cell selection state, keyed by scope.
   * Scope key format: "kind:subworkflowName" or "kind:subworkflowName:nodeId"
   * Shape: { [scopeKey]: string[] }  // array of cell IDs
   */
  cellSelectionByScope: {},

  // ===== NodeObservability: Inspector & Badge State =====

  /**
   * Node badge stats per scope, fetched from backend.
   * Shape: { [scopeKey]: { [nodeId]: BadgeStats } }
   * BadgeStats: { status, lastStart, lastEnd, lastDurationMs, logCounts: {info,warn,error}, writes }
   */
  nodeBadgeStatsByScope: {},

  /**
   * Inspector panel state.
   * - isOpen: whether the inspector panel is visible
   * - tab: current active tab
   * - pinnedNodeId: if set, inspector stays on this node even when selection changes
   */
  inspector: {
    isOpen: false,
    tab: 'overview',  // 'overview' | 'params' | 'context' | 'logs' | 'artifacts'
    pinnedNodeId: null,
  },

  /**
   * Metadata about the last/current run.
   * null if no run has been executed yet.
   */
  lastRunMeta: null,  // { startedAt: string, status: string, endedAt?: string }

  /**
   * Counter that increments each time a simulation run completes.
   * Used to trigger result refreshes in components that display results.
   */
  simulationRunCounter: 0,

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

  // Signal that a simulation run has completed (or started fresh)
  // This increments a counter that components can watch to trigger refreshes
  notifySimulationRunChanged: () => set((state) => ({
    simulationRunCounter: state.simulationRunCounter + 1,
  })),

  // Per-workflow log actions
  addWorkflowLog: (workflowName, type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    set((state) => ({
      workflowLogs: {
        ...state.workflowLogs,
        [workflowName]: [
          ...(state.workflowLogs[workflowName] || []),
          { type, message, timestamp }
        ]
      }
    }));
  },

  clearWorkflowLogs: (workflowName) => {
    set((state) => ({
      workflowLogs: {
        ...state.workflowLogs,
        [workflowName]: []
      }
    }));
  },

  // Call stack log actions
  addCallStackLog: (entry) => {
    set((state) => ({
      callStackLogs: [...state.callStackLogs, entry],
    }));
  },

  clearCallStackLogs: () => set({ callStackLogs: [] }),

  // ===== NodeObservability: Selected Node Actions =====

  /**
   * Set the selected node for a given stage
   * @param {string} stage - The subworkflow stage name
   * @param {string|null} nodeId - The node ID (or null to clear selection)
   */
  setSelectedNode: (stage, nodeId) => {
    set((state) => ({
      selectedNodeByStage: {
        ...state.selectedNodeByStage,
        [stage]: nodeId
      }
    }));
  },

  /**
   * Get the selected node ID for a given stage
   * @param {string} stage - The subworkflow stage name
   * @returns {string|null} The selected node ID or null
   */
  getSelectedNode: (stage) => {
    return get().selectedNodeByStage[stage] || null;
  },

  /**
   * Clear selected node for a given stage
   * @param {string} stage - The subworkflow stage name
   */
  clearSelectedNode: (stage) => {
    set((state) => ({
      selectedNodeByStage: {
        ...state.selectedNodeByStage,
        [stage]: null
      }
    }));
  },

  // ===== NodeObservability: Cell Selection Actions =====

  /**
   * Resolve scope key for cell selection based on subworkflow kind, name, and optionally node ID.
   * Scope key format: "kind:subworkflowName" or "kind:subworkflowName:nodeId"
   * @param {string} kind - 'composer' or 'subworkflow'
   * @param {string} subworkflowName - The subworkflow name
   * @param {string|null} nodeId - Optional node ID for node-level scoping
   * @returns {string} The scope key
   */
  resolveScopeKey: (kind, subworkflowName, nodeId = null) => {
    return nodeId
      ? `${kind}:${subworkflowName}:${nodeId}`
      : `${kind}:${subworkflowName}`;
  },

  /**
   * Get the scope key for the current context (uses current stage and optionally selected node)
   * @param {boolean} includeNode - Whether to include the selected node in the scope
   * @returns {string} The scope key
   */
  getCurrentScopeKey: (includeNode = true) => {
    const state = get();
    const stage = state.currentStage;
    const kind = state.workflow.metadata?.gui?.subworkflow_kinds?.[stage] || 'subworkflow';
    const nodeId = includeNode ? state.selectedNodeByStage[stage] : null;
    return state.resolveScopeKey(kind, stage, nodeId);
  },

  /**
   * Set cell selection for a given scope
   * @param {string} scopeKey - The scope key (from resolveScopeKey)
   * @param {string[]} cellIds - Array of selected cell IDs
   */
  setCellSelection: (scopeKey, cellIds) => {
    set((state) => ({
      cellSelectionByScope: {
        ...state.cellSelectionByScope,
        [scopeKey]: [...cellIds]  // Clone to prevent mutations
      }
    }));
  },

  /**
   * Get cell selection for a given scope
   * @param {string} scopeKey - The scope key (from resolveScopeKey)
   * @returns {string[]} Array of selected cell IDs (empty if none)
   */
  getCellSelection: (scopeKey) => {
    return get().cellSelectionByScope[scopeKey] || [];
  },

  /**
   * Add cell IDs to the selection for a given scope
   * @param {string} scopeKey - The scope key
   * @param {string[]} cellIds - Cell IDs to add
   */
  addToCellSelection: (scopeKey, cellIds) => {
    set((state) => {
      const existing = state.cellSelectionByScope[scopeKey] || [];
      const existingSet = new Set(existing);
      cellIds.forEach(id => existingSet.add(id));
      return {
        cellSelectionByScope: {
          ...state.cellSelectionByScope,
          [scopeKey]: Array.from(existingSet)
        }
      };
    });
  },

  /**
   * Remove cell IDs from the selection for a given scope
   * @param {string} scopeKey - The scope key
   * @param {string[]} cellIds - Cell IDs to remove
   */
  removeFromCellSelection: (scopeKey, cellIds) => {
    set((state) => {
      const existing = state.cellSelectionByScope[scopeKey] || [];
      const removeSet = new Set(cellIds);
      return {
        cellSelectionByScope: {
          ...state.cellSelectionByScope,
          [scopeKey]: existing.filter(id => !removeSet.has(id))
        }
      };
    });
  },

  /**
   * Clear cell selection for a given scope
   * @param {string} scopeKey - The scope key
   */
  clearCellSelection: (scopeKey) => {
    set((state) => ({
      cellSelectionByScope: {
        ...state.cellSelectionByScope,
        [scopeKey]: []
      }
    }));
  },

  /**
   * Clear all cell selections (e.g., when loading a new workflow)
   */
  clearAllCellSelections: () => {
    set({ cellSelectionByScope: {} });
  },

  /**
   * Get the current cell selection (for the current scope based on current stage/node)
   * @param {boolean} includeNode - Whether to use node-level scoping
   * @returns {string[]} Array of selected cell IDs
   */
  getCurrentCellSelection: (includeNode = true) => {
    const state = get();
    const scopeKey = state.getCurrentScopeKey(includeNode);
    return state.getCellSelection(scopeKey);
  },

  /**
   * Set cell selection for the current scope
   * @param {string[]} cellIds - Array of selected cell IDs
   * @param {boolean} includeNode - Whether to use node-level scoping
   */
  setCurrentCellSelection: (cellIds, includeNode = true) => {
    const state = get();
    const scopeKey = state.getCurrentScopeKey(includeNode);
    state.setCellSelection(scopeKey, cellIds);
  },

  // ===== NodeObservability: Inspector Actions =====

  /**
   * Open the inspector panel
   * @param {string|null} tab - Optional tab to open to
   */
  openInspector: (tab = null) => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        isOpen: true,
        ...(tab ? { tab } : {}),
      }
    }));
  },

  /**
   * Close the inspector panel
   */
  closeInspector: () => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        isOpen: false,
      }
    }));
  },

  /**
   * Toggle the inspector panel
   */
  toggleInspector: () => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        isOpen: !state.inspector.isOpen,
      }
    }));
  },

  /**
   * Set the active inspector tab
   * @param {string} tab - 'overview' | 'params' | 'context' | 'logs' | 'artifacts'
   */
  setInspectorTab: (tab) => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        tab,
      }
    }));
  },

  /**
   * Pin the inspector to a specific node (prevents auto-switching on selection change)
   * @param {string|null} nodeId - Node ID to pin to, or null to unpin
   */
  pinInspector: (nodeId) => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        pinnedNodeId: nodeId,
      }
    }));
  },

  /**
   * Toggle inspector pin state for current node
   */
  toggleInspectorPin: () => {
    const state = get();
    const currentStage = state.currentStage;
    const selectedNode = state.selectedNodeByStage[currentStage];
    const isPinned = state.inspector.pinnedNodeId === selectedNode;

    set((state) => ({
      inspector: {
        ...state.inspector,
        pinnedNodeId: isPinned ? null : selectedNode,
      }
    }));
  },

  // ===== NodeObservability: Badge Stats Actions =====

  /**
   * Set badge stats for a scope (usually called after fetching from backend)
   * @param {string} scopeKey - The scope key
   * @param {object} nodeStats - Object mapping nodeId to BadgeStats
   */
  setNodeBadgeStats: (scopeKey, nodeStats) => {
    set((state) => ({
      nodeBadgeStatsByScope: {
        ...state.nodeBadgeStatsByScope,
        [scopeKey]: nodeStats,
      }
    }));
  },

  /**
   * Get badge stats for a specific node
   * @param {string} scopeKey - The scope key
   * @param {string} nodeId - The node ID
   * @returns {object|null} BadgeStats or null
   */
  getNodeBadgeStats: (scopeKey, nodeId) => {
    const state = get();
    return state.nodeBadgeStatsByScope[scopeKey]?.[nodeId] || null;
  },

  /**
   * Clear all badge stats (e.g., before a new run)
   */
  clearNodeBadgeStats: () => {
    set({ nodeBadgeStatsByScope: {} });
  },

  /**
   * Fetch badge stats from the backend API for a specific scope
   * @param {string} scopeKey - The scope key (e.g., "subworkflow:process_cells")
   */
  fetchNodeBadgeStats: async (scopeKey) => {
    const API_BASE_URL = 'http://localhost:5001';
    try {
      const res = await fetch(`${API_BASE_URL}/api/observability/nodes?scopeKey=${encodeURIComponent(scopeKey)}`);
      const data = await res.json();
      if (data.success && data.nodes) {
        set((state) => ({
          nodeBadgeStatsByScope: {
            ...state.nodeBadgeStatsByScope,
            [scopeKey]: data.nodes,
          }
        }));
      }
    } catch (err) {
      console.error('[STORE] Failed to fetch node badge stats:', err);
    }
  },

  /**
   * Fetch badge stats for all subworkflows in the current workflow
   */
  fetchAllBadgeStats: async () => {
    const API_BASE_URL = 'http://localhost:5001';
    const state = get();
    const workflow = state.workflow;
    if (!workflow?.subworkflows) return;

    // Collect all scope keys
    const scopeKeys = Object.keys(workflow.subworkflows).map((name) => {
      const kind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                   (name === 'main' ? 'composer' : 'subworkflow');
      return `${kind}:${name}`;
    });

    // Fetch stats for each scope
    for (const scopeKey of scopeKeys) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/observability/nodes?scopeKey=${encodeURIComponent(scopeKey)}`);
        const data = await res.json();
        if (data.success && data.nodes) {
          set((state) => ({
            nodeBadgeStatsByScope: {
              ...state.nodeBadgeStatsByScope,
              [scopeKey]: data.nodes,
            }
          }));
        }
      } catch (err) {
        console.error(`[STORE] Failed to fetch badge stats for ${scopeKey}:`, err);
      }
    }
  },

  // ===== NodeObservability: Run Meta Actions =====

  /**
   * Set the last run metadata
   * @param {object|null} meta - Run metadata or null to clear
   */
  setLastRunMeta: (meta) => {
    set({ lastRunMeta: meta });
  },

  /**
   * Clear all observability state (call before starting a new run)
   */
  clearObservabilityState: () => {
    set({
      nodeBadgeStatsByScope: {},
      lastRunMeta: null,
    });
  },

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
  loadWorkflow: (workflowJson, filePath = null) => {
    const version = workflowJson.version;

    // Strict v2-only policy
    if (version !== '2.0') {
      const errorMsg = `Unsupported workflow version: ${version || 'undefined'}. Only version 2.0 is supported.`;
      console.error(`[STORE] ${errorMsg}`);
      alert(errorMsg);
      throw new Error(errorMsg);
    }

    // Phase 6: Resolve library paths relative to workflow file
    if (filePath && workflowJson.metadata?.gui?.function_libraries) {
      const workflowDir = pathUtils.dirname(filePath);
      console.log(`[STORE] Resolving library paths relative to: ${workflowDir}`);

      workflowJson.metadata.gui.function_libraries =
        workflowJson.metadata.gui.function_libraries.map(lib => ({
          ...lib,
          path: pathUtils.resolve(lib.path, workflowDir)
        }));
    }

    // Store workflow file path for future exports
    set({ workflowFilePath: filePath });

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

      // Create parameter nodes (supporting regular, list, and dict types)
      const explicitParamNodes = (subworkflow.parameters || []).map((param) => {
        const nodeType = param.type || 'parameterNode';

        if (nodeType === 'listParameterNode') {
          return {
            id: param.id,
            type: 'listParameterNode',
            position: param.position || { x: 0, y: 0 },
            data: {
              label: param.label || 'List',
              listType: param.listType || 'string',
              items: param.items || [],
              targetParam: param.targetParam || 'items',
              onEdit: () => {}
            }
          };
        } else if (nodeType === 'dictParameterNode') {
          return {
            id: param.id,
            type: 'dictParameterNode',
            position: param.position || { x: 0, y: 0 },
            data: {
              label: param.label || 'Dictionary',
              entries: param.entries || [],
              onEdit: () => {}
            }
          };
        } else {
          return {
            id: param.id,
            type: 'parameterNode',
            position: param.position || { x: 0, y: 0 },
            data: {
              label: param.label || 'Parameters',
              parameters: param.parameters || {},
              onEdit: () => {}
            }
          };
        }
      });
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
      // Need to determine the source handle based on param node type
      // and the target handle based on the targetParam for list/dict nodes
      const paramNodeMap = new Map(explicitParamNodes.map(n => [n.id, n]));

      [...(subworkflow.functions || []), ...(subworkflow.subworkflow_calls || [])].forEach((node) => {
        if (node.parameter_nodes && node.parameter_nodes.length > 0) {
          node.parameter_nodes.forEach((paramNodeId) => {
            const paramNode = paramNodeMap.get(paramNodeId);
            // Determine source handle based on node type
            let sourceHandle = 'params';
            let targetHandle = 'params';

            if (paramNode?.type === 'listParameterNode') {
              sourceHandle = 'list-out';
              // Use targetParam to determine which function parameter to connect to
              const targetParam = paramNode.data?.targetParam || 'items';
              targetHandle = `param-${targetParam}`;
            } else if (paramNode?.type === 'dictParameterNode') {
              sourceHandle = 'dict-out';
              // Dict nodes also can have a target parameter
              const targetParam = paramNode.data?.targetParam;
              if (targetParam) {
                targetHandle = `param-${targetParam}`;
              }
            } else {
              // Regular parameter node - infer target from the first parameter key
              const params = paramNode?.data?.parameters || {};
              const paramKeys = Object.keys(params);
              if (paramKeys.length === 1) {
                // Single parameter - connect to that specific handle
                targetHandle = `param-${paramKeys[0]}`;
              } else if (paramKeys.length > 1) {
                // Multiple parameters - use first key as target
                // (In practice, each param node should have one parameter)
                targetHandle = `param-${paramKeys[0]}`;
              }
              // If no params, targetHandle stays as 'params' (will show warning but won't break)
            }

            allEdges.push({
              id: `e-param-${paramNodeId}-${node.id}`,
              source: paramNodeId,
              sourceHandle: sourceHandle,
              target: node.id,
              targetHandle: targetHandle,
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

    // Comprehensive validation before export
    const validationResult = validateWorkflow(workflow, stageNodes);

    if (!validationResult.valid) {
      const errorMessage = 'Workflow validation failed:\n\n' + validationResult.errors.join('\n');
      console.error('[EXPORT] Validation errors:', validationResult.errors);
      alert(errorMessage);
      throw new Error(errorMessage);
    }

    /**
     * Find all nodes reachable from controller node via graph traversal
     * Returns an ordered array of node IDs (functions and subworkflow calls) based on BFS traversal
     */
    const findReachableNodes = (nodes, edges, subworkflowName) => {
      // Find controller node by type (initNode) rather than by ID pattern
      // This handles cases where controller ID doesn't match `controller-${subworkflowName}` exactly
      const controllerNode = nodes.find(n => n.type === 'initNode') ||
                             nodes.find(n => n.id === `controller-${subworkflowName}`);
      if (!controllerNode) return [];
      const controllerNodeId = controllerNode.id;

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
      const listParameterNodes = nodes.filter(n => n.type === 'listParameterNode');
      const dictParameterNodes = nodes.filter(n => n.type === 'dictParameterNode');
      // Find controller node by type (initNode) rather than by ID pattern
      // This handles cases where controller ID doesn't match `controller-${subworkflowName}` exactly
      const controllerNode = nodes.find(n => n.type === 'initNode') ||
                             nodes.find(n => n.id === `controller-${subworkflowName}`);

      // Export ALL function nodes
      const functions = functionNodes.map((node) => {
        // Find parameter connections for this function
        // Include both 'params' (regular parameter nodes) and 'param-' (list/dict parameter nodes)
        const parameterConnections = edges
          .filter(e => e.target === node.id &&
                       (e.targetHandle?.startsWith('params') || e.targetHandle?.startsWith('param-')))
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
        // Include both 'params' (regular parameter nodes) and 'param-' (list/dict parameter nodes)
        const parameterConnections = edges
          .filter(e => e.target === node.id &&
                       (e.targetHandle?.startsWith('params') || e.targetHandle?.startsWith('param-')))
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
          parameter_nodes: parameterConnections
        };

        // Only include results field if it's not empty
        if (node.data.results && node.data.results.trim() !== '') {
          exportedCall.results = node.data.results;
        }

        return exportedCall;
      });

      // Export ALL parameter nodes (regular, list, and dict types)
      const parameters = [
        // Regular parameter nodes
        ...parameterNodes.map((node) => ({
          id: node.id,
          label: node.data.label || 'Parameters',
          parameters: node.data.parameters || {},
          position: node.position,
        })),
        // List parameter nodes
        ...listParameterNodes.map((node) => ({
          id: node.id,
          type: 'listParameterNode',
          label: node.data.label || 'List',
          listType: node.data.listType || 'string',
          items: node.data.items || [],
          targetParam: node.data.targetParam || 'items',
          position: node.position,
        })),
        // Dict parameter nodes
        ...dictParameterNodes.map((node) => ({
          id: node.id,
          type: 'dictParameterNode',
          label: node.data.label || 'Dictionary',
          entries: node.data.entries || [],
          position: node.position,
        })),
      ];

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

    // Phase 6: Make library paths relative to workflow file
    const exportedMetadata = { ...workflow.metadata };
    if (state.workflowFilePath && exportedMetadata.gui?.function_libraries) {
      const workflowDir = pathUtils.dirname(state.workflowFilePath);
      console.log(`[EXPORT] Making library paths relative to: ${workflowDir}`);

      exportedMetadata.gui.function_libraries =
        exportedMetadata.gui.function_libraries.map(lib => ({
          ...lib,
          path: pathUtils.makeRelative(lib.path, workflowDir)
        }));
    }

    return {
      version: '2.0',
      name: workflow.name,
      description: workflow.description,
      metadata: exportedMetadata,
      subworkflows,
    };
  },

  /**
   * Set the workflow file path (for relative path resolution)
   * Phase 6: Path Handling
   */
  setWorkflowFilePath: (filePath) => {
    set({ workflowFilePath: filePath });
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

  // Phase 5: Function Library Management

  /**
   * Add a function library to the workflow
   * @param {string} libraryPath - Path to the library file
   * @param {Object} functionMappings - Map of function names to resolution mode ('overwrite' | 'variant' | 'skip')
   */
  addFunctionLibrary: (libraryPath, functionMappings) => {
    set((state) => {
      const libraries = state.workflow.metadata.gui.function_libraries || [];

      // Check if library already exists
      const existingIndex = libraries.findIndex(lib => lib.path === libraryPath);

      if (existingIndex >= 0) {
        // Update existing library
        libraries[existingIndex] = {
          path: libraryPath,
          functions: functionMappings
        };
      } else {
        // Add new library
        libraries.push({
          path: libraryPath,
          functions: functionMappings
        });
      }

      return {
        workflow: {
          ...state.workflow,
          metadata: {
            ...state.workflow.metadata,
            gui: {
              ...state.workflow.metadata.gui,
              function_libraries: libraries
            }
          }
        }
      };
    });
  },

  /**
   * Remove a function library from the workflow
   * @param {string} libraryPath - Path to the library file
   */
  removeFunctionLibrary: (libraryPath) => {
    set((state) => {
      const libraries = state.workflow.metadata.gui.function_libraries || [];

      return {
        workflow: {
          ...state.workflow,
          metadata: {
            ...state.workflow.metadata,
            gui: {
              ...state.workflow.metadata.gui,
              function_libraries: libraries.filter(lib => lib.path !== libraryPath)
            }
          }
        }
      };
    });
  },

  /**
   * Get all imported function libraries
   * @returns {Array} Array of library objects
   */
  getFunctionLibraries: () => {
    const state = get();
    return state.workflow.metadata?.gui?.function_libraries || [];
  },
}));

export default useWorkflowStore;

