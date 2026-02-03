/**
 * Observability Slice
 *
 * Manages ephemeral UI state for node selection, cell selection,
 * inspector panel, badge stats, and run metadata.
 */

const API_BASE_URL = 'http://localhost:5001';

/**
 * Creates the observability slice for the workflow store
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Observability state and actions
 */
export const createObservabilitySlice = (set, get) => ({
  // ===== Ephemeral UI State =====

  /**
   * Selected node ID per subworkflow stage (ephemeral, UI-only).
   * Shape: { [stageName]: nodeId | null }
   */
  selectedNodeByStage: {},

  /**
   * Ephemeral cell selection state, keyed by scope.
   * Shape: { [scopeKey]: string[] }
   */
  cellSelectionByScope: {},

  // ===== Inspector & Badge State =====

  /**
   * Node badge stats per scope, fetched from backend.
   * Shape: { [scopeKey]: { [nodeId]: BadgeStats } }
   */
  nodeBadgeStatsByScope: {},

  /**
   * Inspector panel state.
   */
  inspector: {
    isOpen: false,
    tab: 'overview',  // 'overview' | 'params' | 'context' | 'logs' | 'artifacts'
    pinnedNodeId: null,
  },

  /**
   * Metadata about the last/current run.
   */
  lastRunMeta: null,

  /**
   * Counter for simulation run refreshes.
   */
  simulationRunCounter: 0,

  // ===== Selected Node Actions =====

  setSelectedNode: (stage, nodeId) => {
    set((state) => ({
      selectedNodeByStage: {
        ...state.selectedNodeByStage,
        [stage]: nodeId
      }
    }));
  },

  getSelectedNode: (stage) => {
    return get().selectedNodeByStage[stage] || null;
  },

  clearSelectedNode: (stage) => {
    set((state) => ({
      selectedNodeByStage: {
        ...state.selectedNodeByStage,
        [stage]: null
      }
    }));
  },

  // ===== Cell Selection Actions =====

  resolveScopeKey: (kind, subworkflowName, nodeId = null) => {
    return nodeId
      ? `${kind}:${subworkflowName}:${nodeId}`
      : `${kind}:${subworkflowName}`;
  },

  getCurrentScopeKey: (includeNode = true) => {
    const state = get();
    const stage = state.currentStage;
    const kind = state.workflow.metadata?.gui?.subworkflow_kinds?.[stage] || 'subworkflow';
    const nodeId = includeNode ? state.selectedNodeByStage[stage] : null;
    return state.resolveScopeKey(kind, stage, nodeId);
  },

  setCellSelection: (scopeKey, cellIds) => {
    set((state) => ({
      cellSelectionByScope: {
        ...state.cellSelectionByScope,
        [scopeKey]: [...cellIds]
      }
    }));
  },

  getCellSelection: (scopeKey) => {
    return get().cellSelectionByScope[scopeKey] || [];
  },

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

  clearCellSelection: (scopeKey) => {
    set((state) => ({
      cellSelectionByScope: {
        ...state.cellSelectionByScope,
        [scopeKey]: []
      }
    }));
  },

  clearAllCellSelections: () => {
    set({ cellSelectionByScope: {} });
  },

  getCurrentCellSelection: (includeNode = true) => {
    const state = get();
    const scopeKey = state.getCurrentScopeKey(includeNode);
    return state.getCellSelection(scopeKey);
  },

  setCurrentCellSelection: (cellIds, includeNode = true) => {
    const state = get();
    const scopeKey = state.getCurrentScopeKey(includeNode);
    state.setCellSelection(scopeKey, cellIds);
  },

  // ===== Inspector Actions =====

  openInspector: (tab = null) => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        isOpen: true,
        ...(tab ? { tab } : {}),
      }
    }));
  },

  closeInspector: () => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        isOpen: false,
      }
    }));
  },

  toggleInspector: () => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        isOpen: !state.inspector.isOpen,
      }
    }));
  },

  setInspectorTab: (tab) => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        tab,
      }
    }));
  },

  pinInspector: (nodeId) => {
    set((state) => ({
      inspector: {
        ...state.inspector,
        pinnedNodeId: nodeId,
      }
    }));
  },

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

  // ===== Badge Stats Actions =====

  setNodeBadgeStats: (scopeKey, nodeStats) => {
    set((state) => ({
      nodeBadgeStatsByScope: {
        ...state.nodeBadgeStatsByScope,
        [scopeKey]: nodeStats,
      }
    }));
  },

  getNodeBadgeStats: (scopeKey, nodeId) => {
    const state = get();
    return state.nodeBadgeStatsByScope[scopeKey]?.[nodeId] || null;
  },

  clearNodeBadgeStats: () => {
    set({ nodeBadgeStatsByScope: {} });
  },

  fetchNodeBadgeStats: async (scopeKey) => {
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

  fetchAllBadgeStats: async () => {
    const state = get();
    const workflow = state.workflow;
    if (!workflow?.subworkflows) return;

    const scopeKeys = Object.keys(workflow.subworkflows).map((name) => {
      const kind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                   (name === 'main' ? 'composer' : 'subworkflow');
      return `${kind}:${name}`;
    });

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

  // ===== Run Meta Actions =====

  setLastRunMeta: (meta) => {
    set({ lastRunMeta: meta });
  },

  clearObservabilityState: () => {
    set({
      nodeBadgeStatsByScope: {},
      lastRunMeta: null,
    });
  },

  notifySimulationRunChanged: () => set((state) => ({
    simulationRunCounter: state.simulationRunCounter + 1,
  })),
});

