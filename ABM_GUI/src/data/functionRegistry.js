/**
 * Function Registry - Catalog of available workflow functions
 * Now dynamically loaded from the Python backend registry
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export const FunctionCategory = {
  INITIALIZATION: 'initialization',
  INTRACELLULAR: 'intracellular',
  DIFFUSION: 'diffusion',
  MICROENVIRONMENT: 'diffusion',  // Map to diffusion category
  INTERCELLULAR: 'intercellular',
  FINALIZATION: 'finalization',
  UTILITY: 'utility',
};

// Global registry cache
let registryCache = null;
let registryPromise = null;

/**
 * Fetch the function registry from the backend
 */
export async function fetchRegistry() {
  // If we already have a promise in flight, return it
  if (registryPromise) {
    return registryPromise;
  }

  // If we have a cached registry, return it
  if (registryCache) {
    return registryCache;
  }

  // Start fetching
  registryPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/registry`);
      const data = await response.json();

      if (data.success) {
        // Convert backend format to frontend format
        const registry = {};
        for (const [name, func] of Object.entries(data.functions)) {
          registry[name] = {
            name: func.name,
            displayName: func.display_name,
            description: func.description,
            category: func.category,
            parameters: func.parameters || [],
            inputs: func.inputs || [],
            outputs: func.outputs || [],
            cloneable: func.cloneable,
            source_file: func.source_file,
            module_path: func.module_path,
          };
        }

        registryCache = registry;
        console.log(`[REGISTRY] Loaded ${Object.keys(registry).length} functions from backend`);
        return registry;
      } else {
        console.error('[REGISTRY] Failed to load registry:', data.error);
        return getFallbackRegistry();
      }
    } catch (error) {
      console.error('[REGISTRY] Error fetching registry:', error);
      return getFallbackRegistry();
    } finally {
      registryPromise = null;
    }
  })();

  return registryPromise;
}

/**
 * Get the registry synchronously (returns cached version or empty object)
 */
export function getRegistrySync() {
  return registryCache || {};
}

/**
 * Fallback registry with minimal functions (used if backend is unavailable)
 */
function getFallbackRegistry() {
  console.warn('[REGISTRY] Using fallback registry');
  return {
  // INTRACELLULAR FUNCTIONS
  update_metabolism: {
    name: 'update_metabolism',
    displayName: 'Update Metabolism',
    description: 'Update intracellular metabolism (ATP, metabolites)',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'src/workflow/functions/intracellular/update_metabolism.py',
  },

  update_gene_networks: {
    name: 'update_gene_networks',
    displayName: 'Update Gene Networks',
    description: 'Update gene network states and propagate signals',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'src/workflow/functions/intracellular/update_gene_networks.py',
  },

  update_phenotypes: {
    name: 'update_phenotypes',
    displayName: 'Update Phenotypes',
    description: 'Update cell phenotypes based on gene expression',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'src/workflow/functions/intracellular/update_phenotypes.py',
  },

  remove_dead_cells: {
    name: 'remove_dead_cells',
    displayName: 'Remove Dead Cells',
    description: 'Remove cells that have died from the population',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'src/workflow/functions/intracellular/remove_dead_cells.py',
  },

  // DIFFUSION FUNCTIONS
  run_diffusion_solver: {
    name: 'run_diffusion_solver',
    displayName: 'Run Diffusion Solver',
    description: 'Run diffusion PDE solver (oxygen, glucose, lactate, H+, pH)',
    category: FunctionCategory.DIFFUSION,
    parameters: [],
    source_file: 'src/workflow/functions/diffusion/run_diffusion_solver.py',
  },

  // INTERCELLULAR FUNCTIONS
  update_cell_division: {
    name: 'update_cell_division',
    displayName: 'Update Cell Division',
    description: 'ATP-based cell division (divide when ATP > threshold)',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [],
    source_file: 'src/workflow/functions/intercellular/update_cell_division.py',
  },

  update_cell_migration: {
    name: 'update_cell_migration',
    displayName: 'Update Cell Migration',
    description: 'Cell migration (placeholder for custom migration logic)',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [],
    source_file: 'src/workflow/functions/intercellular/update_cell_migration.py',
  },

  // DEBUG INITIALIZATION FUNCTIONS
  debug_initialization_1: {
    name: 'debug_initialization_1',
    displayName: 'Debug Initialization 1',
    description: 'Debug function for initialization stage (prints its name and stage)',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] initialization: debug_initialization_1',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_initialization_2: {
    name: 'debug_initialization_2',
    displayName: 'Debug Initialization 2',
    description: 'Debug function for initialization stage (prints its name and stage)',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] initialization: debug_initialization_2',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_initialization_3: {
    name: 'debug_initialization_3',
    displayName: 'Debug Initialization 3',
    description: 'Debug function for initialization stage (prints its name and stage)',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] initialization: debug_initialization_3',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  // DEBUG INTRACELLULAR FUNCTIONS
  debug_intracellular_1: {
    name: 'debug_intracellular_1',
    displayName: 'Debug Intracellular 1',
    description: 'Debug function for intracellular stage (prints its name and stage)',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] intracellular: debug_intracellular_1',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_intracellular_2: {
    name: 'debug_intracellular_2',
    displayName: 'Debug Intracellular 2',
    description: 'Debug function for intracellular stage (prints its name and stage)',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] intracellular: debug_intracellular_2',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_intracellular_3: {
    name: 'debug_intracellular_3',
    displayName: 'Debug Intracellular 3',
    description: 'Debug function for intracellular stage (prints its name and stage)',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] intracellular: debug_intracellular_3',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  // DEBUG MICROENVIRONMENT FUNCTIONS
  debug_microenvironment_1: {
    name: 'debug_microenvironment_1',
    displayName: 'Debug Microenvironment 1',
    description: 'Debug function for microenvironment stage (prints its name and stage)',
    category: FunctionCategory.DIFFUSION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] microenvironment: debug_microenvironment_1',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_microenvironment_2: {
    name: 'debug_microenvironment_2',
    displayName: 'Debug Microenvironment 2',
    description: 'Debug function for microenvironment stage (prints its name and stage)',
    category: FunctionCategory.DIFFUSION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] microenvironment: debug_microenvironment_2',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_microenvironment_3: {
    name: 'debug_microenvironment_3',
    displayName: 'Debug Microenvironment 3',
    description: 'Debug function for microenvironment stage (prints its name and stage)',
    category: FunctionCategory.DIFFUSION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] microenvironment: debug_microenvironment_3',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  // DEBUG INTERCELLULAR FUNCTIONS
  debug_intercellular_1: {
    name: 'debug_intercellular_1',
    displayName: 'Debug Intercellular 1',
    description: 'Debug function for intercellular stage (prints its name and stage)',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] intercellular: debug_intercellular_1',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_intercellular_2: {
    name: 'debug_intercellular_2',
    displayName: 'Debug Intercellular 2',
    description: 'Debug function for intercellular stage (prints its name and stage)',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] intercellular: debug_intercellular_2',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_intercellular_3: {
    name: 'debug_intercellular_3',
    displayName: 'Debug Intercellular 3',
    description: 'Debug function for intercellular stage (prints its name and stage)',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] intercellular: debug_intercellular_3',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  // DEBUG FINALIZATION FUNCTIONS
  debug_finalization_1: {
    name: 'debug_finalization_1',
    displayName: 'Debug Finalization 1',
    description: 'Debug function for finalization stage (prints its name and stage)',
    category: FunctionCategory.FINALIZATION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] finalization: debug_finalization_1',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_finalization_2: {
    name: 'debug_finalization_2',
    displayName: 'Debug Finalization 2',
    description: 'Debug function for finalization stage (prints its name and stage)',
    category: FunctionCategory.FINALIZATION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] finalization: debug_finalization_2',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  debug_finalization_3: {
    name: 'debug_finalization_3',
    displayName: 'Debug Finalization 3',
    description: 'Debug function for finalization stage (prints its name and stage)',
    category: FunctionCategory.FINALIZATION,
    parameters: [
      {
        name: 'message',
        type: 'string',
        description: 'Debug message to print (typically from a connected parameter node)',
        default: '[DEBUG] finalization: debug_finalization_3',
      },
    ],
    source_file: 'src/workflow/functions/debug/debug_dummy_functions.py',
  },

  // =====================================================================
  // OUTPUT/EXPORT FUNCTIONS (CSV, VTK)
  // =====================================================================

  export_csv_checkpoint: {
    name: 'export_csv_checkpoint',
    displayName: 'Export CSV Checkpoint',
    description: 'Export 2D simulation checkpoint (cells + substances) to CSV format',
    category: FunctionCategory.UTILITY,
    parameters: [],
    source_file: 'src/workflow/functions/output/export_csv.py',
  },

  export_csv_checkpoint_conditional: {
    name: 'export_csv_checkpoint_conditional',
    displayName: 'Export CSV Checkpoint (Conditional)',
    description: 'Export CSV checkpoint only if current step matches config.output.save_cellstate_interval',
    category: FunctionCategory.UTILITY,
    parameters: [],
    source_file: 'src/workflow/functions/output/export_csv.py',
  },

  export_csv_cells: {
    name: 'export_csv_cells',
    displayName: 'Export CSV Cells',
    description: 'Export only cell states to CSV format',
    category: FunctionCategory.UTILITY,
    parameters: [],
    source_file: 'src/workflow/functions/output/export_csv.py',
  },

  export_csv_substances: {
    name: 'export_csv_substances',
    displayName: 'Export CSV Substances',
    description: 'Export only substance fields to CSV format',
    category: FunctionCategory.UTILITY,
    parameters: [],
    source_file: 'src/workflow/functions/output/export_csv.py',
  },

  export_vtk_checkpoint: {
    name: 'export_vtk_checkpoint',
    displayName: 'Export VTK Checkpoint',
    description: 'Export 3D simulation checkpoint (cells + substances) to VTK format',
    category: FunctionCategory.UTILITY,
    parameters: [],
    source_file: 'src/workflow/functions/output/export_vtk.py',
  },


  };
}

// Legacy export for backward compatibility (will be empty until registry is loaded)
export const functionRegistry = getRegistrySync();

/**
 * Get functions by category (async version)
 */
export async function getFunctionsByCategoryAsync(category) {
  const registry = await fetchRegistry();
  return Object.values(registry).filter((func) => func.category === category);
}

/**
 * Get functions by category (sync version - uses cached registry)
 */
export const getFunctionsByCategory = (category) => {
  const registry = getRegistrySync();
  return Object.values(registry).filter((func) => func.category === category);
};

/**
 * Get function metadata (async version)
 */
export async function getFunctionAsync(functionName) {
  const registry = await fetchRegistry();
  return registry[functionName];
}

/**
 * Get function metadata (sync version - uses cached registry)
 */
export const getFunction = (functionName) => {
  const registry = getRegistrySync();
  return registry[functionName];
};

/**
 * Get all functions (async version)
 */
export async function getAllFunctionsAsync() {
  const registry = await fetchRegistry();
  return Object.values(registry);
}

/**
 * Get all functions (sync version - uses cached registry)
 */
export const getAllFunctions = () => {
  const registry = getRegistrySync();
  return Object.values(registry);
};

/**
 * Get default parameters for a function
 */
export const getDefaultParameters = (functionName) => {
  const registry = getRegistrySync();
  const func = registry[functionName];
  if (!func) return {};

  const defaults = {};
  (func.parameters || []).forEach((param) => {
    if (param.default !== undefined) {
      defaults[param.name] = param.default;
    }
  });
  return defaults;
};
