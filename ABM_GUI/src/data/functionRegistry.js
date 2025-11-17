/**
 * Function Registry - Catalog of available workflow functions
 * Matches the Python registry in src/workflow/registry.py
 */

export const FunctionCategory = {
  INITIALIZATION: 'initialization',
  INTRACELLULAR: 'intracellular',
  DIFFUSION: 'diffusion',
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

