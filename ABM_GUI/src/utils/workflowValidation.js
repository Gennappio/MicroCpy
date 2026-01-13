/**
 * Workflow Validation Utilities
 * 
 * Provides comprehensive validation for workflow v2.0 structure including:
 * - Call hierarchy rules (composers vs subworkflows)
 * - Cycle detection
 * - Name validity
 * - Reference integrity
 */

const SUBWORKFLOW_NAME_PATTERN = /^[a-zA-Z][a-zA-Z0-9_]*$/;

/**
 * Get the kind of a subworkflow (composer or subworkflow)
 */
export function getSubworkflowKind(workflow, subworkflowName) {
  return workflow.metadata?.gui?.subworkflow_kinds?.[subworkflowName] ||
         (subworkflowName === 'main' ? 'composer' : 'subworkflow');
}

/**
 * Validate subworkflow name format
 */
export function validateSubworkflowName(name) {
  if (!SUBWORKFLOW_NAME_PATTERN.test(name)) {
    return {
      valid: false,
      error: `Invalid subworkflow name '${name}'. Must start with a letter and contain only letters, numbers, and underscores.`
    };
  }
  return { valid: true };
}

/**
 * Validate that a call target exists
 */
export function validateCallTargetExists(workflow, callerName, targetName, nodeId) {
  if (!workflow.subworkflows[targetName]) {
    return {
      valid: false,
      error: `Call node '${nodeId}' in '${callerName}' references missing sub-workflow '${targetName}'.`
    };
  }
  return { valid: true };
}

/**
 * Validate call hierarchy rules (subworkflows cannot call composers)
 */
export function validateCallHierarchy(workflow, callerName, targetName) {
  const callerKind = getSubworkflowKind(workflow, callerName);
  const targetKind = getSubworkflowKind(workflow, targetName);

  if (callerKind === 'subworkflow' && targetKind === 'composer') {
    return {
      valid: false,
      error: `Sub-workflow '${callerName}' cannot call composer '${targetName}'. Only composers can call composers.`
    };
  }
  return { valid: true };
}

/**
 * Validate execution order references
 */
export function validateExecutionOrder(subworkflowName, executionOrder, nodes) {
  const errors = [];
  const nodeIds = new Set(nodes.map(n => n.id));

  executionOrder.forEach(nodeId => {
    if (!nodeIds.has(nodeId)) {
      errors.push(
        `Execution order in '${subworkflowName}' references unknown node ID '${nodeId}'.`
      );
    }
  });

  return errors.length > 0 ? { valid: false, errors } : { valid: true };
}

/**
 * Detect circular dependencies in subworkflow calls using DFS
 * Returns array of cycle paths found
 */
export function detectCycles(workflow, stageNodes) {
  // Build dependency graph: subworkflow -> [called subworkflows]
  const graph = {};
  
  Object.keys(workflow.subworkflows).forEach(subworkflowName => {
    const nodes = stageNodes[subworkflowName] || [];
    const callNodes = nodes.filter(n => n.type === 'subworkflowCall');
    graph[subworkflowName] = callNodes
      .map(n => n.data.subworkflowName)
      .filter(target => target); // Filter out undefined/null
  });

  const cycles = [];
  const visited = new Set();
  const recursionStack = new Set();

  function dfs(node, path = []) {
    visited.add(node);
    recursionStack.add(node);
    path.push(node);

    const neighbors = graph[node] || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        dfs(neighbor, [...path]);
      } else if (recursionStack.has(neighbor)) {
        // Found a cycle
        const cycleStart = path.indexOf(neighbor);
        const cycle = path.slice(cycleStart).concat(neighbor);
        cycles.push(cycle);
      }
    }

    recursionStack.delete(node);
  }

  // Check all nodes for cycles
  Object.keys(graph).forEach(node => {
    if (!visited.has(node)) {
      dfs(node);
    }
  });

  return cycles;
}

/**
 * Format cycle for error message
 */
export function formatCycle(cycle) {
  return cycle.join(' → ');
}

/**
 * Comprehensive workflow validation
 * Returns { valid: boolean, errors: string[] }
 */
export function validateWorkflow(workflow, stageNodes) {
  const errors = [];

  // 1. Validate all subworkflow names
  Object.keys(workflow.subworkflows).forEach(name => {
    const result = validateSubworkflowName(name);
    if (!result.valid) {
      errors.push(result.error);
    }
  });

  // 2. Validate all call nodes
  Object.keys(workflow.subworkflows).forEach(subworkflowName => {
    const nodes = stageNodes[subworkflowName] || [];
    const callNodes = nodes.filter(n => n.type === 'subworkflowCall');

    callNodes.forEach(callNode => {
      const targetName = callNode.data.subworkflowName;

      if (!targetName) {
        errors.push(`Call node '${callNode.id}' in '${subworkflowName}' has no target specified.`);
        return;
      }

      // Check target exists
      const existsResult = validateCallTargetExists(workflow, subworkflowName, targetName, callNode.id);
      if (!existsResult.valid) {
        errors.push(existsResult.error);
        return;
      }

      // Check call hierarchy rules
      const hierarchyResult = validateCallHierarchy(workflow, subworkflowName, targetName);
      if (!hierarchyResult.valid) {
        errors.push(hierarchyResult.error);
      }
    });

    // 3. Validate execution order
    const subworkflow = workflow.subworkflows[subworkflowName];
    if (subworkflow.execution_order && subworkflow.execution_order.length > 0) {
      const orderResult = validateExecutionOrder(
        subworkflowName,
        subworkflow.execution_order,
        nodes
      );
      if (!orderResult.valid) {
        errors.push(...orderResult.errors);
      }
    }
  });

  // 4. Detect circular dependencies
  const cycles = detectCycles(workflow, stageNodes);
  if (cycles.length > 0) {
    cycles.forEach(cycle => {
      errors.push(`Circular dependency detected: ${formatCycle(cycle)}`);
    });
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

