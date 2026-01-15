/**
 * Library Resolver - Utilities for resolving function libraries
 * Per CONTEXT_MANAGEMENT.md Phase 5: Project-Only Libraries
 * 
 * Function libraries are now stored at the project level (project.json)
 * rather than the workflow level. This provides:
 * - Consistent library configuration across all workflows in a project
 * - Simpler workflow files (no library paths embedded)
 * - Easier library management and updates
 */

/**
 * Get effective function libraries for a workflow
 * Merges project-level libraries with any legacy workflow-level libraries
 * 
 * @param {Object} projectConfig - Project configuration (from projectStore)
 * @param {Object} workflowMetadata - Workflow metadata (may contain legacy libraries)
 * @returns {Array} Array of library objects with resolved paths
 */
export const getEffectiveLibraries = (projectConfig, workflowMetadata) => {
  const projectLibraries = projectConfig?.function_libraries || [];
  const workflowLibraries = workflowMetadata?.gui?.function_libraries || [];
  
  // Project libraries take precedence
  // Workflow libraries are only used if no project is loaded (legacy mode)
  if (projectLibraries.length > 0) {
    return projectLibraries;
  }
  
  // Fall back to workflow libraries for backward compatibility
  return workflowLibraries;
};

/**
 * Migrate workflow libraries to project config
 * Used when opening a workflow with embedded libraries in a project context
 * 
 * @param {Array} workflowLibraries - Libraries from workflow metadata
 * @param {Array} projectLibraries - Existing project libraries
 * @returns {Object} { merged: Array, added: Array, conflicts: Array }
 */
export const migrateLibrariesToProject = (workflowLibraries, projectLibraries) => {
  const merged = [...projectLibraries];
  const added = [];
  const conflicts = [];
  
  for (const wfLib of workflowLibraries) {
    const existing = merged.find(pLib => pLib.path === wfLib.path);
    
    if (!existing) {
      // New library - add to project
      merged.push(wfLib);
      added.push(wfLib.path);
    } else {
      // Library exists - check for function conflicts
      const wfFunctions = Object.keys(wfLib.functions || {});
      const pFunctions = Object.keys(existing.functions || {});
      
      const conflictingFunctions = wfFunctions.filter(f => 
        pFunctions.includes(f) && 
        wfLib.functions[f] !== existing.functions[f]
      );
      
      if (conflictingFunctions.length > 0) {
        conflicts.push({
          path: wfLib.path,
          functions: conflictingFunctions
        });
      }
    }
  }
  
  return { merged, added, conflicts };
};

/**
 * Resolve library path relative to project root
 * 
 * @param {string} libraryPath - Library path (may be relative or absolute)
 * @param {string} projectRoot - Project root directory
 * @returns {string} Resolved absolute path
 */
export const resolveLibraryPath = (libraryPath, projectRoot) => {
  if (!libraryPath || !projectRoot) return libraryPath;
  
  // If already absolute, return as-is
  if (libraryPath.startsWith('/') || /^[A-Za-z]:/.test(libraryPath)) {
    return libraryPath;
  }
  
  // Resolve relative to project root
  const normBase = projectRoot.replace(/\\/g, '/').replace(/\/$/, '');
  const parts = libraryPath.split('/');
  const resultParts = normBase.split('/');
  
  for (const part of parts) {
    if (part === '..') {
      resultParts.pop();
    } else if (part !== '.' && part !== '') {
      resultParts.push(part);
    }
  }
  
  return resultParts.join('/');
};

/**
 * Make library path relative to project root
 * 
 * @param {string} absolutePath - Absolute library path
 * @param {string} projectRoot - Project root directory
 * @returns {string} Relative path
 */
export const makeLibraryPathRelative = (absolutePath, projectRoot) => {
  if (!absolutePath || !projectRoot) return absolutePath;
  
  const normAbsolute = absolutePath.replace(/\\/g, '/').replace(/\/$/, '');
  const normBase = projectRoot.replace(/\\/g, '/').replace(/\/$/, '');
  
  const absoluteParts = normAbsolute.split('/');
  const baseParts = normBase.split('/');
  
  // Find common prefix
  let commonLength = 0;
  while (
    commonLength < absoluteParts.length &&
    commonLength < baseParts.length &&
    absoluteParts[commonLength] === baseParts[commonLength]
  ) {
    commonLength++;
  }
  
  // Build relative path
  const upLevels = baseParts.length - commonLength;
  const downPath = absoluteParts.slice(commonLength);
  
  const relativeParts = [];
  for (let i = 0; i < upLevels; i++) {
    relativeParts.push('..');
  }
  relativeParts.push(...downPath);
  
  return relativeParts.join('/');
};

/**
 * Check if a library path is valid (file exists)
 * This is a placeholder - actual validation happens on the backend
 * 
 * @param {string} libraryPath - Path to check
 * @returns {Promise<boolean>} Whether the library exists
 */
export const validateLibraryPath = async (libraryPath) => {
  // TODO: Call backend API to validate path
  return true;
};

export default {
  getEffectiveLibraries,
  migrateLibrariesToProject,
  resolveLibraryPath,
  makeLibraryPathRelative,
  validateLibraryPath
};

