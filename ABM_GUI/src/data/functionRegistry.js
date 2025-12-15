/**
 * Function Registry - Catalog of available workflow functions
 * Matches the Python registry in src/workflow/registry.py
 */

export const FunctionCategory = {
  INITIALIZATION: 'initialization',
  INTRACELLULAR: 'intracellular',
  DIFFUSION: 'microenvironment',  // Renamed from 'diffusion' to 'microenvironment'
  MICROENVIRONMENT: 'microenvironment',  // Alias for clarity
  INTERCELLULAR: 'intercellular',
  FINALIZATION: 'finalization',
  UTILITY: 'utility',
};

export const functionRegistry = {
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

/**
 * Get functions by category
 */
export const getFunctionsByCategory = (category) => {
  return Object.values(functionRegistry).filter((func) => func.category === category);
};

/**
 * Get function metadata
 */
export const getFunction = (functionName) => {
  return functionRegistry[functionName];
};

/**
 * Get all functions
 */
export const getAllFunctions = () => {
  return Object.values(functionRegistry);
};

/**
 * Get default parameters for a function
 */
export const getDefaultParameters = (functionName) => {
  const func = functionRegistry[functionName];
  if (!func) return {};

  const defaults = {};
  func.parameters.forEach((param) => {
    if (param.default !== undefined) {
      defaults[param.name] = param.default;
    }
  });
  return defaults;
};

