/** Function metadata loaded from the running Python backend. */

import { API_BASE_URL } from '../apiConfig';

export const FunctionCategory = {
  INITIALIZATION: 'initialization',
  INTRACELLULAR: 'intracellular',
  DIFFUSION: 'diffusion',
  MICROENVIRONMENT: 'diffusion',
  INTERCELLULAR: 'intercellular',
  FINALIZATION: 'finalization',
  UTILITY: 'utility',
};

let registryCache = null;
let registryPromise = null;

export async function fetchRegistry({ force = false } = {}) {
  if (force) registryCache = null;
  if (registryPromise) return registryPromise;
  if (registryCache) return registryCache;

  registryPromise = (async () => {
    const response = await fetch(`${API_BASE_URL}/api/registry`);
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`Function registry returned HTTP ${response.status}`);
    }
    if (!response.ok || !data.success) {
      throw new Error(data.error || `Function registry returned HTTP ${response.status}`);
    }

    const registry = {};
    for (const [name, func] of Object.entries(data.functions || {})) {
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
        compatible_kernels: func.compatible_kernels || null,
        requires: func.requires || [],
        operates_on: func.operates_on || [],
        contract: func.contract || null,
        validation_errors: func.validation_errors || [],
      };
    }

    registryCache = registry;
    console.log(`[REGISTRY] Loaded ${Object.keys(registry).length} functions from backend`);
    return registry;
  })().finally(() => {
    registryPromise = null;
  });

  return registryPromise;
}

export function getRegistrySync() {
  return registryCache || {};
}

// Retained for source compatibility; dynamic consumers should use the helpers.
export const functionRegistry = {};

function categoryForLookup(category) {
  return category === 'macrostep' ? FunctionCategory.UTILITY : category;
}

export async function getFunctionsByCategoryAsync(category) {
  const registry = await fetchRegistry();
  const backendCategory = categoryForLookup(category);
  return Object.values(registry).filter((func) => func.category === backendCategory);
}

export function getFunctionsByCategory(category) {
  const backendCategory = categoryForLookup(category);
  return Object.values(getRegistrySync()).filter(
    (func) => func.category === backendCategory,
  );
}

export async function getFunctionAsync(functionName) {
  return (await fetchRegistry())[functionName];
}

export function getFunction(functionName) {
  return getRegistrySync()[functionName];
}

export async function getAllFunctionsAsync() {
  return Object.values(await fetchRegistry());
}

export function getAllFunctions() {
  return Object.values(getRegistrySync());
}

export function getDefaultParameters(functionName) {
  const func = getFunction(functionName);
  if (!func) return {};
  return Object.fromEntries(
    (func.parameters || [])
      .filter((parameter) => parameter.default !== undefined)
      .map((parameter) => [parameter.name, parameter.default]),
  );
}
