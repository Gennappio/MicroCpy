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
  // INITIALIZATION FUNCTIONS
  initialize_cell_placement: {
    name: 'initialize_cell_placement',
    displayName: 'Initialize Cell Placement [Legacy]',
    description: 'Place cells in initial configuration (spheroid, grid, or random)',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'initial_cell_count',
        type: 'integer',
        description: 'Number of cells to place initially',
        default: 50,
        required: true,
        min: 1,
        max: 10000,
      },
      {
        name: 'placement_pattern',
        type: 'string',
        description: 'Pattern for cell placement',
        default: 'spheroid',
        required: false,
        options: ['spheroid', 'grid', 'random'],
      },
    ],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  initialize_cell_ages: {
    name: 'initialize_cell_ages',
    displayName: 'Initialize Cell Ages [Legacy]',
    description: 'Set random initial ages for cells',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'max_cell_age',
        type: 'float',
        description: 'Maximum cell age in time units',
        default: 500.0,
        required: true,
        min: 0,
      },
      {
        name: 'cell_cycle_time',
        type: 'float',
        description: 'Cell cycle duration',
        default: 240.0,
        required: true,
        min: 0,
      },
    ],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  // INTRACELLULAR FUNCTIONS (Legacy - use granular functions instead)
  calculate_cell_metabolism: {
    name: 'calculate_cell_metabolism',
    displayName: 'Calculate Cell Metabolism (Legacy)',
    description: '[DEPRECATED] Use "Update Metabolism" instead. Calculate metabolic rates using Michaelis-Menten kinetics',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'oxygen_vmax',
        type: 'float',
        description: 'Maximum oxygen consumption rate',
        default: 1.0e-16,
        required: true,
        min: 0,
      },
      {
        name: 'glucose_vmax',
        type: 'float',
        description: 'Maximum glucose consumption rate',
        default: 3.0e-15,
        required: true,
        min: 0,
      },
      {
        name: 'KO2',
        type: 'float',
        description: 'Michaelis constant for oxygen',
        default: 0.01,
        required: true,
        min: 0,
      },
      {
        name: 'KG',
        type: 'float',
        description: 'Michaelis constant for glucose',
        default: 0.5,
        required: true,
        min: 0,
      },
      {
        name: 'KL',
        type: 'float',
        description: 'Michaelis constant for lactate',
        default: 1.0,
        required: true,
        min: 0,
      },
    ],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  update_cell_metabolic_state: {
    name: 'update_cell_metabolic_state',
    displayName: 'Update Cell Metabolic State (Legacy)',
    description: '[DEPRECATED] Use "Update Metabolism" instead. Update cell metabolic state with ATP and rates',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  // GRANULAR INTRACELLULAR FUNCTIONS
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

  should_divide: {
    name: 'should_divide',
    displayName: 'Check Division (ATP-based) [Legacy]',
    description: '[DEPRECATED] Use "Update Cell Division" instead',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'atp_threshold',
        type: 'float',
        description: 'ATP threshold for division (fraction of max)',
        default: 0.8,
        required: true,
        min: 0,
        max: 1,
      },
      {
        name: 'cell_cycle_time',
        type: 'float',
        description: 'Minimum cell cycle time',
        default: 240.0,
        required: true,
        min: 0,
      },
      {
        name: 'max_atp',
        type: 'float',
        description: 'Maximum ATP value',
        default: 30.0,
        required: true,
        min: 0,
      },
    ],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  update_cell_phenotype: {
    name: 'update_cell_phenotype',
    displayName: 'Update Cell Phenotype [Legacy]',
    description: '[DEPRECATED] Use "Update Phenotypes" instead',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'necrosis_threshold_oxygen',
        type: 'float',
        description: 'Oxygen threshold for necrosis',
        default: 0.011,
        required: true,
        min: 0,
      },
      {
        name: 'necrosis_threshold_glucose',
        type: 'float',
        description: 'Glucose threshold for necrosis',
        default: 0.23,
        required: true,
        min: 0,
      },
    ],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  age_cell: {
    name: 'age_cell',
    displayName: 'Age Cell [Legacy]',
    description: '[DEPRECATED] Aging is now part of "Update Metabolism"',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  check_cell_death: {
    name: 'check_cell_death',
    displayName: 'Check Cell Death [Legacy]',
    description: '[DEPRECATED] Use "Remove Dead Cells" instead',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
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

  select_division_direction: {
    name: 'select_division_direction',
    displayName: 'Select Division Direction [Legacy]',
    description: '[DEPRECATED] Use "Update Cell Division" instead',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  calculate_migration_probability: {
    name: 'calculate_migration_probability',
    displayName: 'Calculate Migration Probability [Legacy]',
    description: '[DEPRECATED] Use "Update Cell Migration" instead',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [
      {
        name: 'base_migration_rate',
        type: 'float',
        description: 'Base migration probability',
        default: 0.0,
        required: true,
        min: 0,
        max: 1,
      },
    ],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
  },

  // FINALIZATION FUNCTIONS
  final_report: {
    name: 'final_report',
    displayName: 'Final Report [Legacy]',
    description: 'Generate comprehensive final simulation report',
    category: FunctionCategory.FINALIZATION,
    parameters: [],
    source_file: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
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

