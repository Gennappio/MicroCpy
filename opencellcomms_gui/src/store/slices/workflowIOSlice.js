/**
 * Workflow I/O Slice
 *
 * Manages loading, exporting, and importing workflows.
 * Handles workflow JSON format conversion, validation,
 * and subworkflow import/export operations.
 */

import { validateWorkflow } from '../../utils/workflowValidation';
import pathUtils from '../pathUtils';

/**
 * Creates the workflow I/O slice
 * @param {Function} set - Zustand set function
 * @param {Function} get - Zustand get function
 * @returns {Object} Workflow I/O actions
 */
export const createWorkflowIOSlice = (set, get) => ({
  // Current workflow file path (for relative path resolution)
  workflowFilePath: null,

  /**
   * Set the workflow file path (for relative path resolution)
   */
  setWorkflowFilePath: (filePath) => {
    set({ workflowFilePath: filePath });
  },

  // Load workflow from JSON - V2-ONLY (no backward compatibility)
  loadWorkflow: (workflowJson, filePath = null) => {
    const version = workflowJson.version;

    // Strict v2-only policy
    if (version !== '2.0') {
      const errorMsg = `Unsupported workflow version: ${version || 'undefined'}. Only version 2.0 is supported.`;
      console.error(`[STORE] ${errorMsg}`);
      alert(errorMsg);
      throw new Error(errorMsg);
    }

    // Phase 6: Resolve library paths relative to workflow file
    if (filePath && workflowJson.metadata?.gui?.function_libraries) {
      const workflowDir = pathUtils.dirname(filePath);
      console.log(`[STORE] Resolving library paths relative to: ${workflowDir}`);

      workflowJson.metadata.gui.function_libraries =
        workflowJson.metadata.gui.function_libraries.map(lib => ({
          ...lib,
          path: pathUtils.resolve(lib.path, workflowDir)
        }));
    }

    // Store workflow file path for future exports
    set({ workflowFilePath: filePath });

    // Load v2.0 sub-workflow format
    get()._loadWorkflowV2(workflowJson);
  },

  // Load v2.0 sub-workflow-based workflow
  _loadWorkflowV2: (workflowJson) => {
    const { subworkflows } = workflowJson;
    if (!subworkflows) {
      console.error('[STORE] No subworkflows found in v2.0 workflow');
      return;
    }
    const newStageNodes = {};
    const newStageEdges = {};

    // Process each sub-workflow
    Object.keys(subworkflows).forEach((subworkflowName) => {
      const subworkflow = subworkflows[subworkflowName];
      const allEdges = [];
      const createdParamNodeIds = new Set();

      // Build execution order for layout
      const executionOrder = subworkflow.execution_order || [];

      // Create controller node
      const controller = subworkflow.controller;
      const controllerNode = controller ? {
        id: controller.id,
        type: 'initNode',
        position: controller.position || { x: 100, y: 100 },
        data: {
          label: controller.label || `${subworkflowName.toUpperCase()} CONTROLLER`,
          numberOfSteps: controller.number_of_steps || 1
        },
        deletable: false
      } : null;

      // Create parameter nodes (supporting regular, list, and dict types)
      const explicitParamNodes = (subworkflow.parameters || []).map((param) => {
        const nodeType = param.type || 'parameterNode';

        if (nodeType === 'listParameterNode') {
          return {
            id: param.id,
            type: 'listParameterNode',
            position: param.position || { x: 0, y: 0 },
            data: {
              label: param.label || 'List',
              listType: param.listType || 'string',
              items: param.items || [],
              targetParam: param.targetParam || 'items',
              onEdit: () => {}
            }
          };
        } else if (nodeType === 'dictParameterNode') {
          return {
            id: param.id,
            type: 'dictParameterNode',
            position: param.position || { x: 0, y: 0 },
            data: {
              label: param.label || 'Dictionary',
              entries: param.entries || [],
              targetParam: param.targetParam,
              onEdit: () => {}
            }
          };
        } else {
          return {
            id: param.id,
            type: 'parameterNode',
            position: param.position || { x: 0, y: 0 },
            data: {
              label: param.label || 'Parameters',
              parameters: param.parameters || {},
              onEdit: () => {}
            }
          };
        }
      });
      explicitParamNodes.forEach(node => createdParamNodeIds.add(node.id));

      // Create function nodes
      const functionNodes = (subworkflow.functions || []).map((func) => ({
        id: func.id,
        type: 'workflowFunction',
        position: func.position || { x: 0, y: 0 },
        data: {
          label: func.function_name,
          functionName: func.function_name,
          parameters: func.parameters || {},
          enabled: func.enabled !== false,
          verbose: func.verbose || false,
          description: func.description || '',
          functionFile: func.function_file || func.parameters?.function_file || '',
          customName: func.custom_name || '',
          stepCount: func.step_count || 1,
          onEdit: () => {}
        }
      }));

      // Create sub-workflow call nodes
      const subworkflowCallNodes = (subworkflow.subworkflow_calls || []).map((call) => ({
        id: call.id,
        type: 'subworkflowCall',
        position: call.position || { x: 0, y: 0 },
        data: {
          label: call.subworkflow_name,
          subworkflowName: call.subworkflow_name,
          iterations: call.iterations || 1,
          parameters: call.parameters || {},
          enabled: call.enabled !== false,
          verbose: call.verbose || false,
          description: call.description || '',
          results: call.results || '',
          onEdit: () => {}
        }
      }));

      // Create parameter edges
      const paramNodeMap = new Map(explicitParamNodes.map(n => [n.id, n]));

      [...(subworkflow.functions || []), ...(subworkflow.subworkflow_calls || [])].forEach((node) => {
        if (node.parameter_nodes && node.parameter_nodes.length > 0) {
          node.parameter_nodes.forEach((paramNodeId) => {
            const paramNode = paramNodeMap.get(paramNodeId);
            let sourceHandle = 'params';
            let targetHandle = 'params';

            if (paramNode?.type === 'listParameterNode') {
              sourceHandle = 'list-out';
              const targetParam = paramNode.data?.targetParam || 'items';
              targetHandle = `param-${targetParam}`;
            } else if (paramNode?.type === 'dictParameterNode') {
              sourceHandle = 'dict-out';
              const targetParam = paramNode.data?.targetParam;
              if (targetParam) {
                targetHandle = `param-${targetParam}`;
              }
            } else {
              const params = paramNode?.data?.parameters || {};
              const paramKeys = Object.keys(params);
              if (paramKeys.length === 1) {
                targetHandle = `param-${paramKeys[0]}`;
              } else if (paramKeys.length > 1) {
                targetHandle = `param-${paramKeys[0]}`;
              }
            }

            allEdges.push({
              id: `e-param-${paramNodeId}-${node.id}`,
              source: paramNodeId,
              sourceHandle: sourceHandle,
              target: node.id,
              targetHandle: targetHandle,
              type: 'default',
              animated: false,
              style: {
                stroke: '#3b82f6',
                strokeWidth: 2,
                strokeDasharray: '5,5'
              }
            });
          });
        }
      });

      // Create execution flow edges based on execution order
      if (controllerNode && executionOrder.length > 0) {
        allEdges.push({
          id: `e-${controllerNode.id}-${executionOrder[0]}`,
          source: controllerNode.id,
          sourceHandle: 'func-out',
          target: executionOrder[0],
          targetHandle: 'func-in',
          type: 'default',
          animated: true,
          markerEnd: {
            type: 'arrowclosed',
            width: 10,
            height: 10
          },
          style: {
            strokeWidth: 6
          }
        });

        for (let i = 0; i < executionOrder.length - 1; i++) {
          allEdges.push({
            id: `e-${executionOrder[i]}-${executionOrder[i + 1]}`,
            source: executionOrder[i],
            sourceHandle: 'func-out',
            target: executionOrder[i + 1],
            targetHandle: 'func-in',
            type: 'default',
            animated: true,
            markerEnd: {
              type: 'arrowclosed',
              width: 10,
              height: 10
            },
            style: {
              strokeWidth: 6
            }
          });
        }
      }

      // Collect all nodes
      const allNodes = [
        ...(controllerNode ? [controllerNode] : []),
        ...functionNodes,
        ...subworkflowCallNodes,
        ...explicitParamNodes
      ];

      newStageNodes[subworkflowName] = allNodes;
      newStageEdges[subworkflowName] = allEdges;
    });

    // Load or infer subworkflow_kinds
    const loadedKinds = workflowJson.metadata?.gui?.subworkflow_kinds || {};
    const subworkflowKinds = {};

    Object.keys(subworkflows).forEach(name => {
      if (loadedKinds[name]) {
        subworkflowKinds[name] = loadedKinds[name];
      } else {
        subworkflowKinds[name] = name === 'main' ? 'composer' : 'subworkflow';
      }
    });

    set((state) => ({
      workflow: {
        ...state.workflow,
        ...workflowJson,
        metadata: {
          ...workflowJson.metadata,
          gui: {
            ...workflowJson.metadata?.gui,
            subworkflow_kinds: subworkflowKinds
          }
        },
        subworkflows: {
          ...subworkflows
        }
      },
      stageNodes: newStageNodes,
      stageEdges: newStageEdges,
      currentStage: 'main'
    }));
  },

  // Export workflow to JSON (V2-only)
  exportWorkflow: () => {
    const state = get();
    const { workflow, stageNodes, stageEdges } = state;

    // Comprehensive validation before export
    const validationResult = validateWorkflow(workflow, stageNodes);

    if (!validationResult.valid) {
      const errorMessage = 'Workflow validation failed:\n\n' + validationResult.errors.join('\n');
      console.error('[EXPORT] Validation errors:', validationResult.errors);
      alert(errorMessage);
      throw new Error(errorMessage);
    }

    /**
     * Find all nodes reachable from controller node via graph traversal
     */
    const findReachableNodes = (nodes, edges, subworkflowName) => {
      const controllerNode = nodes.find(n => n.type === 'initNode') ||
                             nodes.find(n => n.id === `controller-${subworkflowName}`);
      if (!controllerNode) return [];
      const controllerNodeId = controllerNode.id;

      const adjacency = {};
      edges.forEach(edge => {
        if (edge.sourceHandle === 'func-out' || edge.sourceHandle === 'init-out') {
          if (!adjacency[edge.source]) adjacency[edge.source] = [];
          adjacency[edge.source].push(edge.target);
        }
      });

      const visited = new Set();
      const executionOrder = [];
      const queue = [controllerNodeId];
      visited.add(controllerNodeId);

      while (queue.length > 0) {
        const current = queue.shift();
        const neighbors = adjacency[current] || [];

        for (const neighbor of neighbors) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            const node = nodes.find(n => n.id === neighbor);
            if (node && (node.type === 'workflowFunction' || node.type === 'subworkflowCall')) {
              executionOrder.push(neighbor);
            }
            queue.push(neighbor);
          }
        }
      }

      return executionOrder;
    };

    // Convert React Flow nodes back to subworkflows
    const subworkflows = {};
    Object.keys(workflow.subworkflows).forEach((subworkflowName) => {
      const nodes = stageNodes[subworkflowName] || [];
      const edges = stageEdges[subworkflowName] || [];
      const execution_order = findReachableNodes(nodes, edges, subworkflowName);

      const functionNodes = nodes.filter(n => n.type === 'workflowFunction');
      const subworkflowCallNodes = nodes.filter(n => n.type === 'subworkflowCall');
      const parameterNodes = nodes.filter(n => n.type === 'parameterNode');
      const listParameterNodes = nodes.filter(n => n.type === 'listParameterNode');
      const dictParameterNodes = nodes.filter(n => n.type === 'dictParameterNode');
      const controllerNode = nodes.find(n => n.type === 'initNode') ||
                             nodes.find(n => n.id === `controller-${subworkflowName}`);

      // Export ALL function nodes
      const functions = functionNodes.map((node) => {
        const parameterConnections = edges
          .filter(e => e.target === node.id &&
                       (e.targetHandle?.startsWith('params') || e.targetHandle?.startsWith('param-')))
          .map(e => e.source);

        return {
          id: node.id,
          function_name: node.data.functionName,
          function_file: node.data.functionFile || '',
          parameters: node.data.parameters || {},
          enabled: node.data.enabled !== false,
          position: node.position,
          description: node.data.description || '',
          custom_name: node.data.customName || '',
          step_count: node.data.stepCount || 1,
          parameter_nodes: parameterConnections,
        };
      });

      // Export ALL subworkflow call nodes
      const subworkflow_calls = subworkflowCallNodes.map((node) => {
        const parameterConnections = edges
          .filter(e => e.target === node.id &&
                       (e.targetHandle?.startsWith('params') || e.targetHandle?.startsWith('param-')))
          .map(e => e.source);

        const exportedCall = {
          id: node.id,
          type: 'subworkflow_call',
          subworkflow_name: node.data.subworkflowName,
          iterations: node.data.iterations || 1,
          parameters: node.data.parameters || {},
          enabled: node.data.enabled !== false,
          position: node.position,
          description: node.data.description || '',
          parameter_nodes: parameterConnections
        };

        if (node.data.results && node.data.results.trim() !== '') {
          exportedCall.results = node.data.results;
        }

        return exportedCall;
      });

      // Export ALL parameter nodes
      const parameters = [
        ...parameterNodes.map((node) => ({
          id: node.id,
          label: node.data.label || 'Parameters',
          parameters: node.data.parameters || {},
          position: node.position,
        })),
        ...listParameterNodes.map((node) => ({
          id: node.id,
          type: 'listParameterNode',
          label: node.data.label || 'List',
          listType: node.data.listType || 'string',
          items: node.data.items || [],
          targetParam: node.data.targetParam || 'items',
          position: node.position,
        })),
        ...dictParameterNodes.map((node) => ({
          id: node.id,
          type: 'dictParameterNode',
          label: node.data.label || 'Dictionary',
          entries: node.data.entries || [],
          targetParam: node.data.targetParam,
          position: node.position,
        })),
      ];

      // Export controller
      const controller = controllerNode ? {
        id: controllerNode.id,
        type: 'controller',
        label: controllerNode.data.label || `${subworkflowName.toUpperCase()} CONTROLLER`,
        position: controllerNode.position,
        number_of_steps: controllerNode.data.numberOfSteps || 1
      } : null;

      subworkflows[subworkflowName] = {
        description: workflow.subworkflows[subworkflowName]?.description || '',
        enabled: workflow.subworkflows[subworkflowName]?.enabled !== false,
        deletable: workflow.subworkflows[subworkflowName]?.deletable !== false,
        controller,
        functions,
        subworkflow_calls,
        parameters,
        execution_order,
        input_parameters: workflow.subworkflows[subworkflowName]?.input_parameters || []
      };
    });

    // Phase 6: Make library paths relative to workflow file
    const exportedMetadata = { ...workflow.metadata };
    if (state.workflowFilePath && exportedMetadata.gui?.function_libraries) {
      const workflowDir = pathUtils.dirname(state.workflowFilePath);
      console.log(`[EXPORT] Making library paths relative to: ${workflowDir}`);

      exportedMetadata.gui.function_libraries =
        exportedMetadata.gui.function_libraries.map(lib => ({
          ...lib,
          path: pathUtils.makeRelative(lib.path, workflowDir)
        }));
    }

    return {
      version: '2.0',
      name: workflow.name,
      description: workflow.description,
      metadata: exportedMetadata,
      subworkflows,
    };
  },

  // ===== Granular Import/Export Methods =====

  /**
   * Export a single subworkflow to standalone format
   */
  exportSingleSubworkflow: (subworkflowName) => {
    const state = get();
    const { workflow, stageNodes, stageEdges } = state;

    if (!workflow.subworkflows[subworkflowName]) {
      console.error(`[STORE] Subworkflow '${subworkflowName}' not found`);
      return null;
    }

    const subworkflow = workflow.subworkflows[subworkflowName];
    const nodes = stageNodes[subworkflowName] || [];
    const edges = stageEdges[subworkflowName] || [];
    const kind = workflow.metadata?.gui?.subworkflow_kinds?.[subworkflowName] ||
                (subworkflowName === 'main' ? 'composer' : 'subworkflow');

    // Build functions array from nodes
    const functions = nodes
      .filter(node => node.type === 'workflowFunction')
      .map(node => ({
        id: node.id,
        function_name: node.data.functionName,
        parameters: node.data.parameters || {},
        enabled: node.data.enabled !== false,
        verbose: node.data.verbose || false,
        position: node.position,
        description: node.data.description || '',
        custom_name: node.data.customName || '',
        parameter_nodes: node.data.parameterNodes || [],
        step_count: node.data.stepCount || 1,
        ...(node.data.functionFile ? { function_file: node.data.functionFile } : {})
      }));

    // Build subworkflow_calls array from nodes
    const subworkflow_calls = nodes
      .filter(node => node.type === 'subworkflowCall')
      .map(node => ({
        id: node.id,
        subworkflow_name: node.data.subworkflowName,
        iterations: node.data.iterations || 1,
        enabled: node.data.enabled !== false,
        verbose: node.data.verbose || false,
        description: node.data.description || '',
        parameters: node.data.parameters || {},
        context_mapping: node.data.contextMapping || {},
        parameter_nodes: node.data.parameterNodes || [],
        position: node.position
      }));

    // Build parameters array from nodes
    const parameters = nodes
      .filter(node => ['parameterNode', 'listParameterNode', 'dictParameterNode'].includes(node.type))
      .map(node => {
        const baseParam = {
          id: node.id,
          type: node.type,
          position: node.position,
          label: node.data.label || 'Parameters'
        };
        if (node.type === 'parameterNode') {
          return { ...baseParam, parameters: node.data.parameters || {} };
        } else if (node.type === 'listParameterNode') {
          return { ...baseParam, listType: node.data.listType, items: node.data.items || [] };
        } else {
          return { ...baseParam, entries: node.data.entries || [] };
        }
      });

    // Build execution_order from edges
    const execution_order = [];
    const controllerNode = nodes.find(n => n.type === 'initNode');
    if (controllerNode) {
      const visited = new Set();
      const queue = [controllerNode.id];
      while (queue.length > 0) {
        const currentId = queue.shift();
        if (visited.has(currentId)) continue;
        visited.add(currentId);

        const outEdges = edges.filter(e => e.source === currentId);
        for (const edge of outEdges) {
          const targetNode = nodes.find(n => n.id === edge.target);
          if (targetNode && (targetNode.type === 'workflowFunction' || targetNode.type === 'subworkflowCall')) {
            if (!execution_order.includes(edge.target)) {
              execution_order.push(edge.target);
            }
            queue.push(edge.target);
          }
        }
      }
    }

    // Collect dependencies
    const subworkflows_referenced = [...new Set(subworkflow_calls.map(c => c.subworkflow_name))];
    const functions_required = [...new Set(functions.map(f => f.function_name))];

    // Export controller
    const controller = controllerNode ? {
      id: controllerNode.id,
      label: controllerNode.data.label || `${subworkflowName.toUpperCase()} CONTROLLER`,
      position: controllerNode.position,
      number_of_steps: controllerNode.data.numberOfSteps || 1
    } : null;

    return {
      format: 'subworkflow',
      version: '1.0',
      name: subworkflowName,
      kind: kind,
      description: subworkflow.description || '',
      exported_from: workflow.name,
      exported_at: new Date().toISOString(),
      subworkflow: {
        description: subworkflow.description || '',
        enabled: subworkflow.enabled !== false,
        deletable: subworkflow.deletable !== false,
        controller,
        functions,
        subworkflow_calls,
        parameters,
        execution_order,
        input_parameters: subworkflow.input_parameters || []
      },
      dependencies: {
        subworkflows_referenced,
        functions_required
      }
    };
  },

  /**
   * Import a single subworkflow into the current workflow
   */
  importSubworkflow: (name, subworkflowData, kind, options = {}) => {
    const state = get();

    if (state.workflow.subworkflows[name] && !options.overwrite) {
      console.error(`[STORE] Subworkflow '${name}' already exists.`);
      return false;
    }

    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) {
      console.error(`[STORE] Invalid subworkflow name: ${name}`);
      return false;
    }

    if (name === 'main' && options.overwrite) {
      console.error(`[STORE] Cannot overwrite main workflow`);
      return false;
    }

    const swData = subworkflowData.format === 'subworkflow'
      ? subworkflowData.subworkflow
      : subworkflowData;

    // Build nodes from subworkflow data
    const nodes = [];

    // Add controller node
    if (swData.controller) {
      nodes.push({
        id: swData.controller.id || `controller-${name}`,
        type: 'initNode',
        position: swData.controller.position || { x: 100, y: 100 },
        data: {
          label: swData.controller.label || `${name.toUpperCase()} CONTROLLER`,
          numberOfSteps: swData.controller.number_of_steps || 1
        },
        deletable: false
      });
    } else {
      nodes.push({
        id: `controller-${name}`,
        type: 'initNode',
        position: { x: 100, y: 100 },
        data: {
          label: `${name.toUpperCase()} CONTROLLER`,
          numberOfSteps: 1
        },
        deletable: false
      });
    }

    // Add function nodes
    (swData.functions || []).forEach(func => {
      nodes.push({
        id: func.id,
        type: 'workflowFunction',
        position: func.position || { x: 200, y: 100 + nodes.length * 120 },
        data: {
          label: func.custom_name || func.function_name,
          functionName: func.function_name,
          parameters: func.parameters || {},
          enabled: func.enabled !== false,
          verbose: func.verbose || false,
          description: func.description || '',
          customName: func.custom_name || '',
          parameterNodes: func.parameter_nodes || [],
          stepCount: func.step_count || 1,
          ...(func.function_file ? { functionFile: func.function_file } : {})
        }
      });
    });

    // Add subworkflow call nodes
    (swData.subworkflow_calls || []).forEach(call => {
      nodes.push({
        id: call.id,
        type: 'subworkflowCall',
        position: call.position || { x: 200, y: 100 + nodes.length * 120 },
        data: {
          label: call.subworkflow_name,
          subworkflowName: call.subworkflow_name,
          iterations: call.iterations || 1,
          enabled: call.enabled !== false,
          verbose: call.verbose || false,
          description: call.description || '',
          parameters: call.parameters || {},
          contextMapping: call.context_mapping || {},
          parameterNodes: call.parameter_nodes || []
        }
      });
    });

    // Add parameter nodes
    (swData.parameters || []).forEach(param => {
      const nodeData = {
        id: param.id,
        type: param.type || 'parameterNode',
        position: param.position || { x: 400, y: 100 + nodes.length * 120 },
        data: {
          label: param.label || 'Parameters'
        }
      };

      if (param.type === 'listParameterNode') {
        nodeData.data.listType = param.listType || 'string';
        nodeData.data.items = param.items || [];
        nodeData.data.targetParam = param.targetParam || 'items';
      } else if (param.type === 'dictParameterNode') {
        nodeData.data.entries = param.entries || [];
        nodeData.data.targetParam = param.targetParam;
      } else {
        nodeData.data.parameters = param.parameters || {};
      }

      nodes.push(nodeData);
    });

    // Build edges from execution_order
    const edges = [];
    const execution_order = swData.execution_order || [];
    const controllerId = nodes.find(n => n.type === 'initNode')?.id;

    if (controllerId && execution_order.length > 0) {
      edges.push({
        id: `edge-${controllerId}-${execution_order[0]}`,
        source: controllerId,
        target: execution_order[0],
        type: 'smoothstep'
      });

      for (let i = 0; i < execution_order.length - 1; i++) {
        edges.push({
          id: `edge-${execution_order[i]}-${execution_order[i + 1]}`,
          source: execution_order[i],
          target: execution_order[i + 1],
          type: 'smoothstep'
        });
      }
    }

    // Update state
    set((state) => ({
      workflow: {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            subworkflow_kinds: {
              ...state.workflow.metadata.gui.subworkflow_kinds,
              [name]: kind
            }
          }
        },
        subworkflows: {
          ...state.workflow.subworkflows,
          [name]: {
            description: swData.description || '',
            enabled: swData.enabled !== false,
            deletable: swData.deletable !== false,
            controller: swData.controller || {
              id: `controller-${name}`,
              type: 'controller',
              label: `${name.toUpperCase()} CONTROLLER`,
              position: { x: 100, y: 100 },
              number_of_steps: 1
            },
            functions: swData.functions || [],
            subworkflow_calls: swData.subworkflow_calls || [],
            parameters: swData.parameters || [],
            execution_order: execution_order,
            input_parameters: swData.input_parameters || []
          }
        }
      },
      stageNodes: {
        ...state.stageNodes,
        [name]: nodes
      },
      stageEdges: {
        ...state.stageEdges,
        [name]: edges
      }
    }));

    console.log(`[STORE] Imported subworkflow '${name}' as ${kind}`);
    return true;
  },

  /**
   * Recursively collect all transitive dependencies for a set of subworkflows
   */
  collectAllDependencies: (workflowData, selectedNames) => {
    const directSelections = new Set(selectedNames);
    const allSubworkflows = new Set(selectedNames);
    const visited = new Set();
    const queue = [...selectedNames];
    const functionLibraries = new Set();
    const missingDependencies = new Set();
    const dependencies = new Map();

    while (queue.length > 0) {
      const name = queue.shift();
      if (visited.has(name)) continue;
      visited.add(name);

      const subworkflow = workflowData.subworkflows?.[name];
      if (!subworkflow) {
        if (!directSelections.has(name)) {
          missingDependencies.add(name);
        }
        continue;
      }

      const directDeps = new Set();

      for (const call of subworkflow.subworkflow_calls || []) {
        const refName = call.subworkflow_name;
        directDeps.add(refName);

        if (!allSubworkflows.has(refName)) {
          if (workflowData.subworkflows?.[refName]) {
            allSubworkflows.add(refName);
            queue.push(refName);
          } else {
            missingDependencies.add(refName);
          }
        }
      }

      dependencies.set(name, directDeps);

      for (const func of subworkflow.functions || []) {
        if (func.function_file) {
          functionLibraries.add(func.function_file);
        }
      }
    }

    console.log('[STORE] Collected dependencies:', {
      selected: [...directSelections],
      allSubworkflows: [...allSubworkflows],
      functionLibraries: [...functionLibraries],
      missingDependencies: [...missingDependencies]
    });

    return {
      allSubworkflows,
      directSelections,
      dependencies,
      functionLibraries,
      missingDependencies
    };
  },

  /**
   * Import multiple subworkflows from a full workflow file
   */
  importSubworkflowsFromWorkflow: (workflowData, subworkflowNames, options = {}) => {
    const results = {
      success: [],
      failed: [],
      warnings: [],
      autoDependencies: []
    };

    const renameMap = options.renameMap || {};
    const skipDependencies = options.skipDependencies || false;

    let namesToImport = [...subworkflowNames];
    let dependencyInfo = null;

    if (!skipDependencies) {
      dependencyInfo = get().collectAllDependencies(workflowData, subworkflowNames);
      namesToImport = [...dependencyInfo.allSubworkflows];

      for (const name of namesToImport) {
        if (!dependencyInfo.directSelections.has(name)) {
          results.autoDependencies.push(name);
        }
      }

      for (const missing of dependencyInfo.missingDependencies) {
        results.warnings.push({
          name: missing,
          warning: `Dependency '${missing}' not found in source workflow`
        });
      }
    }

    // Topological sort for import order
    const importOrder = [];
    const imported = new Set();

    const addWithDeps = (name) => {
      if (imported.has(name)) return;
      if (!workflowData.subworkflows?.[name]) return;

      const sw = workflowData.subworkflows[name];
      for (const call of sw.subworkflow_calls || []) {
        const depName = call.subworkflow_name;
        if (namesToImport.includes(depName) && !imported.has(depName)) {
          addWithDeps(depName);
        }
      }

      if (!imported.has(name)) {
        importOrder.push(name);
        imported.add(name);
      }
    };

    for (const name of namesToImport) {
      addWithDeps(name);
    }

    // Import in correct order
    for (const originalName of importOrder) {
      if (!workflowData.subworkflows[originalName]) {
        results.failed.push({ name: originalName, error: 'Subworkflow not found in source' });
        continue;
      }

      const targetName = renameMap[originalName] || originalName;
      const kind = workflowData.metadata?.gui?.subworkflow_kinds?.[originalName] ||
                  (originalName === 'main' ? 'composer' : 'subworkflow');

      if (originalName === 'main' && !renameMap[originalName]) {
        results.warnings.push({
          name: originalName,
          warning: "Skipped 'main' - use renameMap to import with different name"
        });
        continue;
      }

      const state = get();
      if (state.workflow.subworkflows[targetName] && !options.overwrite) {
        if (results.autoDependencies.includes(originalName)) {
          console.log(`[STORE] Skipping auto-dependency '${originalName}' - already exists`);
          continue;
        }
        results.failed.push({ name: originalName, error: 'Already exists' });
        continue;
      }

      const subworkflowData = workflowData.subworkflows[originalName];
      const success = get().importSubworkflow(targetName, subworkflowData, kind, {
        overwrite: options.overwrite
      });

      if (success) {
        const isAutoDep = results.autoDependencies.includes(originalName);
        results.success.push({
          original: originalName,
          imported: targetName,
          kind,
          isAutoDependency: isAutoDep
        });
      } else {
        results.failed.push({ name: originalName, error: 'Import failed' });
      }
    }

    console.log('[STORE] Import results:', results);
    return results;
  },

  /**
   * Get list of subworkflows from a workflow file for selection
   */
  getSubworkflowsFromWorkflowData: (workflowData) => {
    if (!workflowData?.subworkflows) {
      return [];
    }

    return Object.entries(workflowData.subworkflows).map(([name, sw]) => {
      const kind = workflowData.metadata?.gui?.subworkflow_kinds?.[name] ||
                  (name === 'main' ? 'composer' : 'subworkflow');

      const functionCount = (sw.functions || []).length;
      const callCount = (sw.subworkflow_calls || []).length;
      const dependencies = (sw.subworkflow_calls || []).map(c => c.subworkflow_name);

      return {
        name,
        kind,
        description: sw.description || '',
        functionCount,
        callCount,
        dependencies,
        enabled: sw.enabled !== false
      };
    });
  },
});