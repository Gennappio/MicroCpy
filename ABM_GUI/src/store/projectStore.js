import { create } from 'zustand';

/**
 * Project Store - Manages project configuration and context registry
 * Per CONTEXT_MANAGEMENT.md specification v1.1
 */

// API base URL - consistent with functionRegistry.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

// Engine-provided keys that are prepopulated in every new registry
const ENGINE_PROVIDED_KEYS = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    name: 'dt',
    aliases: [],
    type: { kind: 'primitive', name: 'float' },
    write_policy: 'read_only',
    delete_policy: 'forbidden',
    description: 'Simulation timestep',
    tags: ['engine', 'core'],
    example: 0.1,
    owner: 'engine',
    visibility: 'normal',
    deprecated: false
  },
  {
    id: '00000000-0000-0000-0000-000000000002',
    name: 'results_dir',
    aliases: [],
    type: { kind: 'primitive', name: 'string' },
    write_policy: 'read_only',
    delete_policy: 'forbidden',
    description: 'Top-level results directory',
    tags: ['engine', 'core'],
    example: '/path/to/results',
    owner: 'engine',
    visibility: 'hidden',
    deprecated: false
  },
  {
    id: '00000000-0000-0000-0000-000000000003',
    name: 'subworkflow_name',
    aliases: [],
    type: { kind: 'primitive', name: 'string' },
    write_policy: 'read_only',
    delete_policy: 'forbidden',
    description: 'Current subworkflow name',
    tags: ['engine'],
    example: 'main',
    owner: 'engine',
    visibility: 'hidden',
    deprecated: false
  },
  {
    id: '00000000-0000-0000-0000-000000000004',
    name: 'subworkflow_kind',
    aliases: [],
    type: { kind: 'primitive', name: 'string' },
    write_policy: 'read_only',
    delete_policy: 'forbidden',
    description: 'Current subworkflow kind (composer/subworkflow)',
    tags: ['engine'],
    example: 'composer',
    owner: 'engine',
    visibility: 'hidden',
    deprecated: false
  },
  {
    id: '00000000-0000-0000-0000-000000000005',
    name: 'subworkflow_results_dir',
    aliases: [],
    type: { kind: 'primitive', name: 'string' },
    write_policy: 'read_only',
    delete_policy: 'forbidden',
    description: 'Current subworkflow results directory',
    tags: ['engine'],
    example: '/path/to/results/subworkflows/analysis',
    owner: 'engine',
    visibility: 'hidden',
    deprecated: false
  }
];

// Generate UUID v4
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

// Validate context key name pattern
const KEY_NAME_PATTERN = /^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$/;

const validateKeyName = (name) => {
  return KEY_NAME_PATTERN.test(name);
};

// Create default project config
const createDefaultProjectConfig = (projectName = 'Untitled Project') => ({
  schema_version: 1,
  project_id: generateUUID(),
  name: projectName,
  context_registry_path: '.microc/context_registry.json',
  context_enforcement: 'strict',
  function_libraries: []
});

// Create default context registry
const createDefaultContextRegistry = (projectId) => ({
  schema_version: 1,
  project_id: projectId,
  revision: 1,
  keys: [...ENGINE_PROVIDED_KEYS]
});

const useProjectStore = create((set, get) => ({
  // Project state
  projectRoot: null,
  projectConfig: null,
  contextRegistry: null,
  isProjectLoaded: false,
  lastKnownRevision: null,
  
  // UI state
  showRegistryPanel: false,
  registrySearchQuery: '',
  registryFilter: 'all', // 'all', 'normal', 'advanced', 'hidden', 'deprecated'
  
  // Error state
  lastError: null,
  
  // Actions
  setProjectRoot: (path) => set({ projectRoot: path }),
  
  setShowRegistryPanel: (show) => set({ showRegistryPanel: show }),
  
  setRegistrySearchQuery: (query) => set({ registrySearchQuery: query }),
  
  setRegistryFilter: (filter) => set({ registryFilter: filter }),
  
  clearError: () => set({ lastError: null }),

  /**
   * Create a new project in the given directory
   */
  createProject: async (projectRoot, projectName) => {
    try {
      const config = createDefaultProjectConfig(projectName);
      const registry = createDefaultContextRegistry(config.project_id);

      // Call backend to create project files
      const response = await fetch(`${API_BASE_URL}/api/project/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_root: projectRoot,
          config,
          registry
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create project');
      }

      set({
        projectRoot,
        projectConfig: config,
        contextRegistry: registry,
        isProjectLoaded: true,
        lastKnownRevision: registry.revision,
        lastError: null
      });

      return { success: true };
    } catch (error) {
      set({ lastError: error.message });
      return { success: false, error: error.message };
    }
  },

  /**
   * Open an existing project
   */
  openProject: async (projectRoot) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/project/open`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_root: projectRoot })
      });

      const data = await response.json();

      if (!response.ok) {
        // Project doesn't exist - need to prompt for creation
        if (data.needs_creation) {
          return { success: false, needs_creation: true };
        }
        throw new Error(data.error || 'Failed to open project');
      }

      set({
        projectRoot,
        projectConfig: data.config,
        contextRegistry: data.registry,
        isProjectLoaded: true,
        lastKnownRevision: data.registry.revision,
        lastError: null
      });

      return { success: true };
    } catch (error) {
      set({ lastError: error.message });
      return { success: false, error: error.message };
    }
  },

  /**
   * Close the current project
   */
  closeProject: () => {
    set({
      projectRoot: null,
      projectConfig: null,
      contextRegistry: null,
      isProjectLoaded: false,
      lastKnownRevision: null,
      lastError: null
    });
  },

  /**
   * Save project config
   */
  saveProjectConfig: async () => {
    const { projectRoot, projectConfig } = get();
    if (!projectRoot || !projectConfig) return { success: false, error: 'No project loaded' };

    try {
      const response = await fetch(`${API_BASE_URL}/api/project/save-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_root: projectRoot,
          config: projectConfig
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to save project config');
      }

      return { success: true };
    } catch (error) {
      set({ lastError: error.message });
      return { success: false, error: error.message };
    }
  },

  /**
   * Save context registry with optimistic concurrency control
   */
  saveContextRegistry: async () => {
    const { projectRoot, contextRegistry, lastKnownRevision } = get();
    if (!projectRoot || !contextRegistry) return { success: false, error: 'No project loaded' };

    try {
      const response = await fetch(`${API_BASE_URL}/api/project/save-registry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_root: projectRoot,
          registry: contextRegistry,
          expected_revision: lastKnownRevision
        })
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.revision_conflict) {
          // Revision conflict - registry was modified externally
          return {
            success: false,
            revision_conflict: true,
            current_revision: data.current_revision,
            error: 'Registry was modified by another process. Please reload and re-apply changes.'
          };
        }
        throw new Error(data.error || 'Failed to save registry');
      }

      // Update with new revision
      set({
        contextRegistry: { ...contextRegistry, revision: data.new_revision },
        lastKnownRevision: data.new_revision
      });

      return { success: true };
    } catch (error) {
      set({ lastError: error.message });
      return { success: false, error: error.message };
    }
  },

  /**
   * Reload context registry from disk
   */
  reloadContextRegistry: async () => {
    const { projectRoot } = get();
    if (!projectRoot) return { success: false, error: 'No project loaded' };

    try {
      const response = await fetch(`${API_BASE_URL}/api/project/reload-registry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_root: projectRoot })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to reload registry');
      }

      const data = await response.json();

      set({
        contextRegistry: data.registry,
        lastKnownRevision: data.registry.revision
      });

      return { success: true };
    } catch (error) {
      set({ lastError: error.message });
      return { success: false, error: error.message };
    }
  },

  // ============ Context Key Management ============

  /**
   * Get all context keys (optionally filtered)
   */
  getContextKeys: (filter = 'all') => {
    const { contextRegistry, registrySearchQuery } = get();
    if (!contextRegistry) return [];

    let keys = contextRegistry.keys || [];

    // Apply visibility filter
    if (filter !== 'all') {
      if (filter === 'deprecated') {
        keys = keys.filter(k => k.deprecated);
      } else {
        keys = keys.filter(k => k.visibility === filter && !k.deprecated);
      }
    }

    // Apply search query
    if (registrySearchQuery) {
      const query = registrySearchQuery.toLowerCase();
      keys = keys.filter(k =>
        k.name.toLowerCase().includes(query) ||
        (k.description && k.description.toLowerCase().includes(query)) ||
        (k.aliases && k.aliases.some(a => a.toLowerCase().includes(query))) ||
        (k.tags && k.tags.some(t => t.toLowerCase().includes(query)))
      );
    }

    return keys;
  },

  /**
   * Get a context key by ID
   */
  getContextKeyById: (id) => {
    const { contextRegistry } = get();
    if (!contextRegistry) return null;
    return contextRegistry.keys.find(k => k.id === id);
  },

  /**
   * Get a context key by name (or alias)
   */
  getContextKeyByName: (name) => {
    const { contextRegistry } = get();
    if (!contextRegistry) return null;
    return contextRegistry.keys.find(k =>
      k.name === name || (k.aliases && k.aliases.includes(name))
    );
  },

  /**
   * Create a new context key
   */
  createContextKey: (keyData) => {
    const { contextRegistry } = get();
    if (!contextRegistry) return { success: false, error: 'No project loaded' };

    // Validate name
    if (!validateKeyName(keyData.name)) {
      return {
        success: false,
        error: 'Invalid key name. Must match pattern: lowercase letters, numbers, underscores, dots for namespacing'
      };
    }

    // Check for duplicate name
    const existing = get().getContextKeyByName(keyData.name);
    if (existing) {
      return { success: false, error: `Key with name "${keyData.name}" already exists` };
    }

    // Check aliases for duplicates
    if (keyData.aliases) {
      for (const alias of keyData.aliases) {
        const existingAlias = get().getContextKeyByName(alias);
        if (existingAlias) {
          return { success: false, error: `Alias "${alias}" conflicts with existing key` };
        }
      }
    }

    const newKey = {
      id: generateUUID(),
      name: keyData.name,
      aliases: keyData.aliases || [],
      type: keyData.type || { kind: 'any' },
      write_policy: keyData.write_policy || 'read_write',
      delete_policy: keyData.delete_policy || 'allowed',
      description: keyData.description || '',
      tags: keyData.tags || [],
      example: keyData.example,
      owner: keyData.owner || 'user',
      visibility: keyData.visibility || 'normal',
      deprecated: false
    };

    set({
      contextRegistry: {
        ...contextRegistry,
        keys: [...contextRegistry.keys, newKey]
      }
    });

    return { success: true, key: newKey };
  },

  /**
   * Update an existing context key
   */
  updateContextKey: (id, updates) => {
    const { contextRegistry } = get();
    if (!contextRegistry) return { success: false, error: 'No project loaded' };

    const keyIndex = contextRegistry.keys.findIndex(k => k.id === id);
    if (keyIndex === -1) {
      return { success: false, error: 'Key not found' };
    }

    const existingKey = contextRegistry.keys[keyIndex];

    // Cannot modify engine-provided keys (except visibility/deprecated)
    if (existingKey.owner === 'engine') {
      const allowedUpdates = ['visibility', 'deprecated'];
      const attemptedUpdates = Object.keys(updates);
      const disallowed = attemptedUpdates.filter(u => !allowedUpdates.includes(u));
      if (disallowed.length > 0) {
        return { success: false, error: `Cannot modify engine-provided key properties: ${disallowed.join(', ')}` };
      }
    }

    // Validate name if being changed
    if (updates.name && updates.name !== existingKey.name) {
      if (!validateKeyName(updates.name)) {
        return { success: false, error: 'Invalid key name format' };
      }
      const existing = get().getContextKeyByName(updates.name);
      if (existing && existing.id !== id) {
        return { success: false, error: `Key with name "${updates.name}" already exists` };
      }
    }

    const updatedKey = { ...existingKey, ...updates };
    const newKeys = [...contextRegistry.keys];
    newKeys[keyIndex] = updatedKey;

    set({
      contextRegistry: {
        ...contextRegistry,
        keys: newKeys
      }
    });

    return { success: true, key: updatedKey };
  },

  /**
   * Delete a context key
   */
  deleteContextKey: (id) => {
    const { contextRegistry } = get();
    if (!contextRegistry) return { success: false, error: 'No project loaded' };

    const key = contextRegistry.keys.find(k => k.id === id);
    if (!key) {
      return { success: false, error: 'Key not found' };
    }

    // Cannot delete engine-provided keys
    if (key.delete_policy === 'forbidden') {
      return { success: false, error: 'Cannot delete this key (delete_policy: forbidden)' };
    }

    set({
      contextRegistry: {
        ...contextRegistry,
        keys: contextRegistry.keys.filter(k => k.id !== id)
      }
    });

    return { success: true };
  },

  /**
   * Deprecate a context key (soft delete)
   */
  deprecateContextKey: (id, replacement = null) => {
    return get().updateContextKey(id, {
      deprecated: true,
      deprecated_replacement: replacement
    });
  },

  /**
   * Add function library to project
   */
  addFunctionLibrary: (libraryPath) => {
    const { projectConfig } = get();
    if (!projectConfig) return { success: false, error: 'No project loaded' };

    if (projectConfig.function_libraries.includes(libraryPath)) {
      return { success: false, error: 'Library already added' };
    }

    set({
      projectConfig: {
        ...projectConfig,
        function_libraries: [...projectConfig.function_libraries, libraryPath]
      }
    });

    return { success: true };
  },

  /**
   * Remove function library from project
   */
  removeFunctionLibrary: (libraryPath) => {
    const { projectConfig } = get();
    if (!projectConfig) return { success: false, error: 'No project loaded' };

    set({
      projectConfig: {
        ...projectConfig,
        function_libraries: projectConfig.function_libraries.filter(l => l !== libraryPath)
      }
    });

    return { success: true };
  },

  /**
   * Update context enforcement mode
   */
  setContextEnforcement: (mode) => {
    const { projectConfig } = get();
    if (!projectConfig) return { success: false, error: 'No project loaded' };

    if (!['strict', 'warn', 'off'].includes(mode)) {
      return { success: false, error: 'Invalid enforcement mode' };
    }

    set({
      projectConfig: {
        ...projectConfig,
        context_enforcement: mode
      }
    });

    return { success: true };
  }
}));

// Export utilities for use elsewhere
export { generateUUID, validateKeyName, ENGINE_PROVIDED_KEYS };
export default useProjectStore;
