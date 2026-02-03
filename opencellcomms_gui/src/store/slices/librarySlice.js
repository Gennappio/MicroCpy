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
});

