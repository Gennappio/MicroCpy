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
    displayName: 'Initialize Cell Placement',
    description: 'Place cells in initial configuration (spheroid, grid, or random)',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
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
  },

  initialize_cell_ages: {
    name: 'initialize_cell_ages',
    displayName: 'Initialize Cell Ages',
    description: 'Set random initial ages for cells',
    category: FunctionCategory.INITIALIZATION,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
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
  },

  // INTRACELLULAR FUNCTIONS
  calculate_cell_metabolism: {
    name: 'calculate_cell_metabolism',
    displayName: 'Calculate Cell Metabolism',
    description: 'Calculate metabolic rates using Michaelis-Menten kinetics',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
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
  },

  update_cell_metabolic_state: {
    name: 'update_cell_metabolic_state',
    displayName: 'Update Cell Metabolic State',
    description: 'Update cell metabolic state with ATP and rates',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
    ],
  },

  should_divide: {
    name: 'should_divide',
    displayName: 'Check Division (ATP-based)',
    description: 'Determine if cell should divide based on ATP and age',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
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
  },

  update_cell_phenotype: {
    name: 'update_cell_phenotype',
    displayName: 'Update Cell Phenotype',
    description: 'Update phenotype based on gene network state',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
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
  },

  age_cell: {
    name: 'age_cell',
    displayName: 'Age Cell',
    description: 'Increment cell age by time step',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
    ],
  },

  check_cell_death: {
    name: 'check_cell_death',
    displayName: 'Check Cell Death',
    description: 'Check if cell should die based on phenotype',
    category: FunctionCategory.INTRACELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
    ],
  },

  // INTERCELLULAR FUNCTIONS
  select_division_direction: {
    name: 'select_division_direction',
    displayName: 'Select Division Direction',
    description: 'Choose direction for cell division',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
    ],
  },

  calculate_migration_probability: {
    name: 'calculate_migration_probability',
    displayName: 'Calculate Migration Probability',
    description: 'Calculate probability of cell migration',
    category: FunctionCategory.INTERCELLULAR,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
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
  },

  // FINALIZATION FUNCTIONS
  final_report: {
    name: 'final_report',
    displayName: 'Final Report',
    description: 'Generate comprehensive final simulation report',
    category: FunctionCategory.FINALIZATION,
    parameters: [
      {
        name: 'function_file',
        type: 'string',
        description: 'Path to Python file containing this function',
        default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
        required: true,
      },
    ],
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

