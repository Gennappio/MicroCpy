/**
 * Log Slice
 *
 * Manages simulation logs, per-workflow logs, and call stack logs.
 */

/**
 * Creates the log management slice
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Log management state and actions
 */
export const createLogSlice = (set, get) => ({
  // Simulation logs (persistent across tab changes)
  simulationLogs: [],

  // Per-workflow logs (for integrated console)
  workflowLogs: {},

  // Call stack logs (for sub-workflow debugging)
  callStackLogs: [],

  // Simulation log actions
  addSimulationLog: (type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    set((state) => ({
      simulationLogs: [...state.simulationLogs, { type, message, timestamp }],
    }));
  },

  clearSimulationLogs: () => set({ simulationLogs: [] }),

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
});

