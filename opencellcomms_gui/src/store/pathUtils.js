/**
 * Path Utilities for Phase 6: Path Handling
 *
 * Provides utilities for handling relative and absolute paths
 * when loading/exporting workflows and function libraries.
 */

/**
 * Make a path relative to a base directory
 * @param {string} absolutePath - The absolute path to convert
 * @param {string} basePath - The base directory path
 * @returns {string} Relative path
 */
export function makeRelative(absolutePath, basePath) {
  if (!absolutePath || !basePath) return absolutePath;

  // Normalize paths (remove trailing slashes)
  const normAbsolute = absolutePath.replace(/\\/g, '/').replace(/\/$/, '');
  const normBase = basePath.replace(/\\/g, '/').replace(/\/$/, '');

  // Split into parts
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
}

/**
 * Resolve a relative path against a base directory
 * @param {string} relativePath - The relative path to resolve
 * @param {string} basePath - The base directory path
 * @returns {string} Absolute path
 */
export function resolve(relativePath, basePath) {
  if (!relativePath || !basePath) return relativePath;

  // If path is already absolute, return as-is
  if (relativePath.startsWith('/') || /^[A-Za-z]:/.test(relativePath)) {
    return relativePath;
  }

  // Normalize base path
  const normBase = basePath.replace(/\\/g, '/').replace(/\/$/, '');

  // Split paths
  const baseParts = normBase.split('/');
  const relativeParts = relativePath.split('/');

  // Process relative parts
  const resultParts = [...baseParts];
  for (const part of relativeParts) {
    if (part === '..') {
      resultParts.pop();
    } else if (part !== '.' && part !== '') {
      resultParts.push(part);
    }
  }

  return resultParts.join('/');
}

/**
 * Get directory path from file path
 * @param {string} filePath - Full file path
 * @returns {string} Directory path
 */
export function dirname(filePath) {
  if (!filePath) return '';
  const normalized = filePath.replace(/\\/g, '/');
  const lastSlash = normalized.lastIndexOf('/');
  return lastSlash >= 0 ? normalized.substring(0, lastSlash) : '';
}

// Default export for compatibility
const pathUtils = {
  makeRelative,
  resolve,
  dirname
};

export default pathUtils;

