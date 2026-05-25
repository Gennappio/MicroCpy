/**
 * Library Slice
 *
 * Manages function library imports and management for Phase 5
 * function library support.
 */

/**
 * Creates the function library management slice
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Library management actions
 */
export const createLibrarySlice = (set, get) => ({
  /**
   * Add a function library to the workflow
   * @param {string} libraryPath - Path to the library file
   * @param {Object} functionMappings - Map of function names to resolution mode
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

  /**
   * Add a library loaded from a workflow JSON file.
   * Extracts function names used in the workflow and stores them with workflow metadata.
   */
  addWorkflowLibrary: (workflowName, workflowPath, functionNames) => {
    set((state) => {
      const libraries = state.workflow.metadata.gui.function_libraries || [];
      const existingIndex = libraries.findIndex((lib) => lib.path === workflowPath);
      const newLib = {
        type: 'workflow',
        name: workflowName,
        path: workflowPath,
        functions: functionNames,
      };
      const updated = existingIndex >= 0
        ? libraries.map((l, i) => (i === existingIndex ? newLib : l))
        : [...libraries, newLib];

      return {
        workflow: {
          ...state.workflow,
          metadata: {
            ...state.workflow.metadata,
            gui: { ...state.workflow.metadata.gui, function_libraries: updated },
          },
        },
      };
    });
  },

  /**
   * Add a user-created function to project metadata.
   * Each entry: { name, category, adapter, behavior, parameters: [{name,type,default}] }
   */
  addUserFunction: (functionDef) => {
    set((state) => {
      const existing = state.workflow.metadata.gui.user_functions || [];
      if (existing.some((f) => f.name === functionDef.name)) return state;
      return {
        workflow: {
          ...state.workflow,
          metadata: {
            ...state.workflow.metadata,
            gui: {
              ...state.workflow.metadata.gui,
              user_functions: [...existing, functionDef],
            },
          },
        },
      };
    });
  },

  markUserFunctionExported: (functionName) => {
    set((state) => ({
      workflow: {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            user_functions: (state.workflow.metadata.gui.user_functions || []).map((f) =>
              f.name === functionName ? { ...f, exported: true } : f
            ),
          },
        },
      },
    }));
  },

  removeUserFunction: (functionName) => {
    set((state) => ({
      workflow: {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            user_functions: (state.workflow.metadata.gui.user_functions || []).filter(
              (f) => f.name !== functionName
            ),
          },
        },
      },
    }));
  },
});

