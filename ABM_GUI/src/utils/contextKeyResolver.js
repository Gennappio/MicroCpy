/**
 * Context Key Resolver - Utilities for ID ↔ Name conversion
 * Per CONTEXT_MANAGEMENT.md Phase 2: Export/Import
 * 
 * Internal storage uses UUIDs for stability during renames.
 * Export/Import uses human-readable names for portability.
 */

/**
 * Build lookup maps from a context registry
 * @param {Object} registry - The context registry object
 * @returns {Object} { idToName, nameToId, aliasToId }
 */
export const buildRegistryMaps = (registry) => {
  const idToName = new Map();
  const nameToId = new Map();
  const aliasToId = new Map();

  if (!registry || !registry.keys) {
    return { idToName, nameToId, aliasToId };
  }

  for (const key of registry.keys) {
    idToName.set(key.id, key.name);
    nameToId.set(key.name, key.id);
    
    // Also map aliases
    if (key.aliases) {
      for (const alias of key.aliases) {
        aliasToId.set(alias, key.id);
      }
    }
  }

  return { idToName, nameToId, aliasToId };
};

/**
 * Resolve a key name (or alias) to its ID
 * @param {string} name - Key name or alias
 * @param {Object} registry - Context registry
 * @returns {string|null} Key ID or null if not found
 */
export const resolveNameToId = (name, registry) => {
  const { nameToId, aliasToId } = buildRegistryMaps(registry);
  return nameToId.get(name) || aliasToId.get(name) || null;
};

/**
 * Resolve a key ID to its canonical name
 * @param {string} id - Key ID
 * @param {Object} registry - Context registry
 * @returns {string|null} Key name or null if not found
 */
export const resolveIdToName = (id, registry) => {
  const { idToName } = buildRegistryMaps(registry);
  return idToName.get(id) || null;
};

/**
 * Convert workflow parameters from name-based to ID-based
 * Used during import
 * @param {Object} parameters - Parameters object with name-based keys
 * @param {Object} registry - Context registry
 * @param {Object} options - { strict: boolean, onUnresolved: (name) => void }
 * @returns {Object} { converted: Object, unresolved: string[] }
 */
export const convertParametersToIds = (parameters, registry, options = {}) => {
  const { strict = false, onUnresolved = null } = options;
  const { nameToId, aliasToId } = buildRegistryMaps(registry);
  const converted = {};
  const unresolved = [];

  for (const [key, value] of Object.entries(parameters || {})) {
    // Check if value is a context key reference (starts with $)
    if (typeof value === 'string' && value.startsWith('$')) {
      const keyName = value.slice(1); // Remove $ prefix
      const keyId = nameToId.get(keyName) || aliasToId.get(keyName);
      
      if (keyId) {
        converted[key] = `$${keyId}`;
      } else {
        unresolved.push(keyName);
        if (onUnresolved) onUnresolved(keyName);
        if (!strict) {
          // In non-strict mode, keep the original name
          converted[key] = value;
        }
      }
    } else {
      // Not a context key reference, keep as-is
      converted[key] = value;
    }
  }

  return { converted, unresolved };
};

/**
 * Convert workflow parameters from ID-based to name-based
 * Used during export
 * @param {Object} parameters - Parameters object with ID-based keys
 * @param {Object} registry - Context registry
 * @returns {Object} { converted: Object, unresolved: string[] }
 */
export const convertParametersToNames = (parameters, registry) => {
  const { idToName } = buildRegistryMaps(registry);
  const converted = {};
  const unresolved = [];

  for (const [key, value] of Object.entries(parameters || {})) {
    // Check if value is a context key reference (starts with $)
    if (typeof value === 'string' && value.startsWith('$')) {
      const keyId = value.slice(1); // Remove $ prefix
      const keyName = idToName.get(keyId);
      
      if (keyName) {
        converted[key] = `$${keyName}`;
      } else {
        unresolved.push(keyId);
        // Keep the ID if name not found (shouldn't happen normally)
        converted[key] = value;
      }
    } else {
      // Not a context key reference, keep as-is
      converted[key] = value;
    }
  }

  return { converted, unresolved };
};

/**
 * Convert an entire workflow from name-based to ID-based context keys
 * Used during import
 * @param {Object} workflow - Workflow JSON
 * @param {Object} registry - Context registry
 * @returns {Object} { workflow: Object, unresolvedKeys: string[] }
 */
export const convertWorkflowToIds = (workflow, registry) => {
  const unresolvedKeys = new Set();
  const converted = JSON.parse(JSON.stringify(workflow)); // Deep clone

  // Process each subworkflow
  for (const [name, subworkflow] of Object.entries(converted.subworkflows || {})) {
    // Convert function parameters
    for (const func of subworkflow.functions || []) {
      const result = convertParametersToIds(func.parameters, registry);
      func.parameters = result.converted;
      result.unresolved.forEach(k => unresolvedKeys.add(k));
    }

    // Convert subworkflow call parameters
    for (const call of subworkflow.subworkflow_calls || []) {
      const result = convertParametersToIds(call.parameters, registry);
      call.parameters = result.converted;
      result.unresolved.forEach(k => unresolvedKeys.add(k));
    }

    // Convert parameter node parameters
    for (const param of subworkflow.parameters || []) {
      const result = convertParametersToIds(param.parameters, registry);
      param.parameters = result.converted;
      result.unresolved.forEach(k => unresolvedKeys.add(k));
    }
  }

  return { workflow: converted, unresolvedKeys: Array.from(unresolvedKeys) };
};

/**
 * Convert an entire workflow from ID-based to name-based context keys
 * Used during export
 * @param {Object} workflow - Workflow JSON (with ID-based keys)
 * @param {Object} registry - Context registry
 * @returns {Object} { workflow: Object, unresolvedIds: string[] }
 */
export const convertWorkflowToNames = (workflow, registry) => {
  const unresolvedIds = new Set();
  const converted = JSON.parse(JSON.stringify(workflow)); // Deep clone

  // Process each subworkflow
  for (const [name, subworkflow] of Object.entries(converted.subworkflows || {})) {
    // Convert function parameters
    for (const func of subworkflow.functions || []) {
      const result = convertParametersToNames(func.parameters, registry);
      func.parameters = result.converted;
      result.unresolved.forEach(id => unresolvedIds.add(id));
    }

    // Convert subworkflow call parameters
    for (const call of subworkflow.subworkflow_calls || []) {
      const result = convertParametersToNames(call.parameters, registry);
      call.parameters = result.converted;
      result.unresolved.forEach(id => unresolvedIds.add(id));
    }

    // Convert parameter node parameters
    for (const param of subworkflow.parameters || []) {
      const result = convertParametersToNames(param.parameters, registry);
      param.parameters = result.converted;
      result.unresolved.forEach(id => unresolvedIds.add(id));
    }
  }

  return { workflow: converted, unresolvedIds: Array.from(unresolvedIds) };
};

/**
 * Validate that all context key references in a workflow exist in the registry
 * @param {Object} workflow - Workflow JSON
 * @param {Object} registry - Context registry
 * @returns {Object} { valid: boolean, missingKeys: string[] }
 */
export const validateWorkflowContextKeys = (workflow, registry) => {
  const { nameToId, aliasToId } = buildRegistryMaps(registry);
  const missingKeys = new Set();

  const checkValue = (value) => {
    if (typeof value === 'string' && value.startsWith('$')) {
      const keyRef = value.slice(1);
      // Check if it's a name, alias, or ID
      if (!nameToId.has(keyRef) && !aliasToId.has(keyRef)) {
        // Could be an ID - check if it looks like a UUID
        const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(keyRef);
        if (!isUUID) {
          missingKeys.add(keyRef);
        }
      }
    }
  };

  // Check all subworkflows
  for (const subworkflow of Object.values(workflow.subworkflows || {})) {
    // Check function parameters
    for (const func of subworkflow.functions || []) {
      for (const value of Object.values(func.parameters || {})) {
        checkValue(value);
      }
    }

    // Check subworkflow call parameters
    for (const call of subworkflow.subworkflow_calls || []) {
      for (const value of Object.values(call.parameters || {})) {
        checkValue(value);
      }
    }

    // Check parameter node parameters
    for (const param of subworkflow.parameters || []) {
      for (const value of Object.values(param.parameters || {})) {
        checkValue(value);
      }
    }
  }

  return {
    valid: missingKeys.size === 0,
    missingKeys: Array.from(missingKeys)
  };
};

/**
 * Create missing context keys from a workflow
 * Used during import when keys don't exist in registry
 * @param {string[]} keyNames - Array of key names to create
 * @param {Function} createKeyFn - Function to create a key (from projectStore)
 * @returns {Object} { created: string[], failed: string[] }
 */
export const createMissingKeys = (keyNames, createKeyFn) => {
  const created = [];
  const failed = [];

  for (const name of keyNames) {
    const result = createKeyFn({
      name,
      description: `Auto-created during workflow import`,
      type: { kind: 'any' },
      write_policy: 'read_write',
      visibility: 'normal',
      tags: ['imported']
    });

    if (result.success) {
      created.push(name);
    } else {
      failed.push(name);
    }
  }

  return { created, failed };
};

