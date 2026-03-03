/**
 * Planner Slice
 *
 * Manages multiple named parameter configurations ("planner tabs").
 * Each tab holds a snapshot of parameter node data (parameterOverrides)
 * that is independent of the canvas nodes.
 */

import { snapshotAllParamNodeData } from '../../utils/extractConnectedParams';

let nextTabCounter = 1;

/**
 * Creates the planner slice
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Planner actions and state
 */
export const createPlannerSlice = (set, get) => ({
  // Array of { id, name, enabled, parameterOverrides: { paramNodeId: paramNodeData } }
  plannerTabs: [],

  // Currently viewed tab id
  activePlannerTabId: null,

  /**
   * Add a new planner tab by snapshotting current canvas param values.
   */
  addPlannerTab: () => {
    const { stageNodes, stageEdges, workflow, plannerTabs } = get();
    const overrides = snapshotAllParamNodeData(stageNodes, stageEdges, workflow.metadata);
    const id = `planner-tab-${Date.now()}-${nextTabCounter}`;
    const name = `Run ${nextTabCounter}`;
    nextTabCounter++;

    const newTab = { id, name, enabled: true, parameterOverrides: overrides };

    set({
      plannerTabs: [...plannerTabs, newTab],
      activePlannerTabId: id,
    });
  },

  /**
   * Remove a planner tab. Switches active if needed.
   */
  removePlannerTab: (tabId) => {
    const { plannerTabs, activePlannerTabId } = get();
    const filtered = plannerTabs.filter((t) => t.id !== tabId);
    let newActive = activePlannerTabId;

    if (activePlannerTabId === tabId) {
      newActive = filtered.length > 0 ? filtered[filtered.length - 1].id : null;
    }

    set({ plannerTabs: filtered, activePlannerTabId: newActive });
  },

  /**
   * Rename a planner tab.
   */
  renamePlannerTab: (tabId, newName) => {
    set((state) => ({
      plannerTabs: state.plannerTabs.map((t) =>
        t.id === tabId ? { ...t, name: newName } : t
      ),
    }));
  },

  /**
   * Toggle a planner tab's enabled state.
   */
  togglePlannerTab: (tabId) => {
    set((state) => ({
      plannerTabs: state.plannerTabs.map((t) =>
        t.id === tabId ? { ...t, enabled: !t.enabled } : t
      ),
    }));
  },

  /**
   * Set the active (currently viewed) planner tab.
   */
  setActivePlannerTab: (tabId) => {
    set({ activePlannerTabId: tabId });
  },

  /**
   * Update a parameter value within a tab's overrides.
   * @param {string} tabId
   * @param {string} paramNodeId
   * @param {Function} updater - (oldData) => newData
   */
  updatePlannerTabParam: (tabId, paramNodeId, updater) => {
    set((state) => ({
      plannerTabs: state.plannerTabs.map((t) => {
        if (t.id !== tabId) return t;
        const oldData = t.parameterOverrides[paramNodeId];
        if (!oldData) return t;
        return {
          ...t,
          parameterOverrides: {
            ...t.parameterOverrides,
            [paramNodeId]: updater(oldData),
          },
        };
      }),
    }));
  },

  /**
   * Bulk set planner tabs (for workflow load).
   */
  setPlannerTabs: (tabs) => {
    // Reset counter based on loaded tabs
    const maxNum = tabs.reduce((max, t) => {
      const match = t.name.match(/^Run (\d+)$/);
      return match ? Math.max(max, parseInt(match[1], 10)) : max;
    }, 0);
    nextTabCounter = maxNum + 1;

    set({
      plannerTabs: tabs,
      activePlannerTabId: tabs.length > 0 ? tabs[0].id : null,
    });
  },

  /**
   * Get all enabled planner tabs in order.
   */
  getActivePlannerTabs: () => {
    return get().plannerTabs.filter((t) => t.enabled);
  },
});
