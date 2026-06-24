/**
 * Workflow I/O Slice
 *
 * Manages loading, exporting, and importing workflows.
 * Handles workflow JSON format conversion, validation,
 * and subworkflow import/export operations.
 */

import { validateWorkflow } from '../../utils/workflowValidation';
import pathUtils from '../pathUtils';
import { computeSubworkflowKinds } from '../computeSubworkflowKinds';
import { INIT_SEQUENCE_NAME } from '../subworkflowKinds';
import {
  assembleSubworkflowsFromStages,
  deriveForEachForBehavior,
} from '../../utils/assembleWorkflow';

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

    // A behavior file (.subworkflow.json) is not a full workflow — point the
    // user at the right place instead of complaining about its version.
    if (workflowJson.format === 'subworkflow') {
      const errorMsg =
        'This is a behavior file (.subworkflow.json), not a full workflow. ' +
        'Load it from the Library panel\'s "Load File" button instead.';
      console.error(`[STORE] ${errorMsg}`);
      alert(errorMsg);
      throw new Error(errorMsg);
    }

    // Strict v2-only policy
    if (version !== '2.0') {
      const errorMsg = `Unsupported workflow version: ${version || 'undefined'}. Only version 2.0 is supported.`;
      console.error(`[STORE] ${errorMsg}`);
      alert(errorMsg);
      throw new Error(errorMsg);
    }

    // Strict taxonomy enforcement: only load workflows whose `metadata.gui` carries
    // the exact set of keys the GUI itself produces. Any key the GUI cannot author
    // (a removed/renamed category or a stray key) is refused rather than silently
    // half-loaded, since unknown structure can leave the GUI in a broken state. A
    // workflow with no `gui` block (a bare composable/processing workflow) is allowed.
    const gui = workflowJson.metadata?.gui;
    if (gui && typeof gui === 'object' && !Array.isArray(gui)) {
      const ALLOWED_GUI_KEYS = new Set([
        'agent_kinds', 'resource_kinds', 'world', 'scheduler', 'processing',
        'init_sequence', 'function_libraries', 'user_functions',
        'main_is_synthesized', 'contract_enforcement', 'planner', 'subworkflow_kinds',
      ]);
      const unknownKeys = Object.keys(gui).filter((k) => !ALLOWED_GUI_KEYS.has(k));
      if (unknownKeys.length > 0) {
        const errorMsg =
          'This workflow uses metadata.gui keys the current taxonomy does not support: ' +
          `${unknownKeys.join(', ')}. Only workflows authored with the current GUI taxonomy can be loaded.`;
        console.error(`[STORE] ${errorMsg}`);
        alert(errorMsg);
        throw new Error(errorMsg);
      }
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
              // Canonical JSON key is snake_case target_param (used by
              // hand-authored workflows and the codegen). Fall back to camelCase
              // for files previously written by the GUI.
              targetParam: param.target_param ?? param.targetParam ?? 'items',
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
              targetParam: param.target_param ?? param.targetParam,
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
      // Note: onEdit is a live callback injected by WorkflowCanvas on mount — never stored here.
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
          contract: func.contract || null,
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
          forEach: call.for_each || null,
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

      // Reconstruct the scheduler-style "Number of steps" parameter edge:
      // a parameter node wired to the controller's steps-param handle. It is
      // persisted as controller.parameter_nodes (mirroring the parameter_nodes
      // convention used by functions/calls, but the target is the controller).
      if (controllerNode && Array.isArray(controller?.parameter_nodes)) {
        controller.parameter_nodes.forEach((paramNodeId) => {
          const paramNode = paramNodeMap.get(paramNodeId);
          allEdges.push({
            id: `e-steps-${paramNodeId}-${controllerNode.id}`,
            source: paramNodeId,
            sourceHandle: 'params',
            target: controllerNode.id,
            targetHandle: 'steps-param',
            type: 'default',
            animated: false,
            style: { stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '5,5' },
          });
          // Pre-seed display/connection data so the count is correct before the
          // canvas effect runs.
          const stepsVal = paramNode?.data?.parameters?.steps
            ?? paramNode?.data?.parameters?.step_count
            ?? paramNode?.data?.parameters?.numberOfSteps;
          controllerNode.data.isStepsParameterConnected = true;
          if (stepsVal !== undefined) {
            controllerNode.data.connectedStepsValue = stepsVal;
            controllerNode.data.numberOfSteps = stepsVal;
          }
        });
      }

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

    // ABM metadata is optional. A workflow may use a bare composable/processing
    // structure (e.g. main → child composers, or just a processing canvas)
    // without the full agent/world/scheduler scaffolding. Normalize any
    // missing ABM fields to well-formed (always-iterable) shapes so such
    // workflows both load AND can be edited — the ABM mutators (abmSlice) assume
    // these arrays/objects always exist and would otherwise crash on first edit.
    const guiMeta = (workflowJson.metadata && workflowJson.metadata.gui) || {};
    const rawWorld = (guiMeta.world && typeof guiMeta.world === 'object') ? guiMeta.world : {};
    const rawSched = (guiMeta.scheduler && typeof guiMeta.scheduler === 'object') ? guiMeta.scheduler : {};
    const rawProc = (guiMeta.processing && typeof guiMeta.processing === 'object') ? guiMeta.processing : {};
    const agentKinds = (Array.isArray(guiMeta.agent_kinds) ? guiMeta.agent_kinds : []).map((k) => ({
      ...k,
      behavior_subworkflows: Array.isArray(k?.behavior_subworkflows) ? k.behavior_subworkflows : [],
    }));
    const resourceKinds = (Array.isArray(guiMeta.resource_kinds) ? guiMeta.resource_kinds : []).map((k) => ({
      ...k,
      behavior_subworkflows: Array.isArray(k?.behavior_subworkflows) ? k.behavior_subworkflows : [],
    }));
    const world = {
      ...rawWorld,
      subworkflow: rawWorld.subworkflow || null,
      behavior_subworkflows: Array.isArray(rawWorld.behavior_subworkflows) ? rawWorld.behavior_subworkflows : [],
    };
    const scheduler = { ...rawSched, subworkflow: rawSched.subworkflow || '__scheduler__' };
    const processing = {
      ...rawProc,
      behavior_subworkflows: Array.isArray(rawProc.behavior_subworkflows) ? rawProc.behavior_subworkflows : [],
    };
    const mainIsSynthesized = guiMeta.main_is_synthesized || false;
    const userFunctions = guiMeta.user_functions || [];

    // Phase 14C: Initialization sequence. If the workflow lacks an
    // `__init_sequence__` subworkflow (or it's empty), auto-populate it from
    // world.subworkflow + each agent_kinds[i].init_subworkflow in
    // array order. This is a one-shot bootstrap that keeps Phase-13-era
    // workflows running without manual edits — user-reordering after this
    // never re-fires the auto-populate because the seq won't be empty.
    const initSeqMeta = guiMeta.init_sequence || { subworkflow: INIT_SEQUENCE_NAME };
    const initSeqName = initSeqMeta.subworkflow || INIT_SEQUENCE_NAME;
    const existingInitSeq = subworkflows[initSeqName];
    const initSeqIsEmpty = !existingInitSeq || (existingInitSeq.subworkflow_calls || []).length === 0;

    if (initSeqIsEmpty) {
      const autoOrder = [];
      if (world.subworkflow) autoOrder.push(world.subworkflow);
      resourceKinds.forEach((k) => { if (k.init_subworkflow) autoOrder.push(k.init_subworkflow); });
      agentKinds.forEach((k) => { if (k.init_subworkflow) autoOrder.push(k.init_subworkflow); });

      const newCalls = autoOrder.map((name, i) => ({
        id: `init-call-${name}-${i}`,
        type: 'subworkflow_call',
        subworkflow_name: name,
        iterations: 1,
        parameters: {},
        enabled: true,
        position: { x: 400, y: 100 + i * 120 },
        description: name,
        parameter_nodes: [],
      }));

      const baseSw = existingInitSeq || {
        description: 'Initialization order — drag init subworkflows here',
        enabled: true,
        deletable: false,
        controller: {
          id: `controller-${initSeqName}`,
          type: 'controller',
          label: 'INIT SEQUENCE',
          position: { x: 100, y: 100 },
          number_of_steps: 1,
        },
        functions: [],
        parameters: [],
        input_parameters: [],
      };
      const populatedSw = {
        ...baseSw,
        subworkflow_calls: newCalls,
        execution_order: newCalls.map((c) => c.id),
      };
      subworkflows[initSeqName] = populatedSw;

      const controllerId = populatedSw.controller.id;
      const seqNodes = [
        {
          id: controllerId,
          type: 'initNode',
          position: populatedSw.controller.position || { x: 100, y: 100 },
          data: { label: populatedSw.controller.label, numberOfSteps: 1 },
          deletable: false,
        },
        ...newCalls.map((call) => ({
          id: call.id,
          type: 'subworkflowCall',
          position: call.position,
          data: {
            label: call.subworkflow_name,
            subworkflowName: call.subworkflow_name,
            iterations: 1,
            enabled: true,
            description: call.description,
          },
        })),
      ];

      const seqEdges = [];
      if (newCalls.length > 0) {
        seqEdges.push({
          id: `e-${controllerId}-${newCalls[0].id}`,
          source: controllerId,
          sourceHandle: 'func-out',
          target: newCalls[0].id,
          targetHandle: 'func-in',
          type: 'default',
          animated: true,
          markerEnd: { type: 'arrowclosed', width: 10, height: 10 },
          style: { strokeWidth: 6 },
        });
        for (let i = 0; i < newCalls.length - 1; i++) {
          seqEdges.push({
            id: `e-${newCalls[i].id}-${newCalls[i + 1].id}`,
            source: newCalls[i].id,
            sourceHandle: 'func-out',
            target: newCalls[i + 1].id,
            targetHandle: 'func-in',
            type: 'default',
            animated: true,
            markerEnd: { type: 'arrowclosed', width: 10, height: 10 },
            style: { strokeWidth: 6 },
          });
        }
      }
      newStageNodes[initSeqName] = seqNodes;
      newStageEdges[initSeqName] = seqEdges;
    }

    // Phase 14B: derive subworkflow_kinds from ABM metadata (never read from JSON).
    const guiWithInitSeq = {
      ...guiMeta,
      world,
      init_sequence: initSeqMeta,
      agent_kinds: agentKinds,
      resource_kinds: resourceKinds,
      scheduler,
      processing,
    };
    const subworkflowKinds = computeSubworkflowKinds({
      metadata: { gui: guiWithInitSeq },
      subworkflows,
    });
    const orphans = Object.keys(subworkflows).filter((n) => !(n in subworkflowKinds));
    if (orphans.length > 0) {
      // Non-fatal: unreferenced subworkflows are allowed (e.g. a work-in-progress
      // canvas, or a composable workflow whose children aren't ABM-mapped). They
      // still load; just warn rather than blocking the import.
      console.warn(
        `[STORE] Subworkflows not referenced by any ABM field: ${orphans.join(', ')}. Loading anyway.`
      );
    }

    // Determine initial stage: prefer scheduler, else first non-synthesized subworkflow
    const schedulerName = scheduler.subworkflow || '__scheduler__';
    const initialStage = newStageNodes[schedulerName] ? schedulerName :
      (mainIsSynthesized ? Object.keys(subworkflows).find(n => n !== 'main') || 'main' : 'main');

    set((state) => ({
      workflow: {
        ...state.workflow,
        ...workflowJson,
        metadata: {
          ...workflowJson.metadata,
          gui: {
            ...guiMeta,
            subworkflow_kinds: subworkflowKinds,
            agent_kinds: agentKinds,
            resource_kinds: resourceKinds,
            world,
            init_sequence: initSeqMeta,
            scheduler,
            processing,
            main_is_synthesized: mainIsSynthesized,
            user_functions: userFunctions,
          }
        },
        subworkflows,
      },
      stageNodes: newStageNodes,
      stageEdges: newStageEdges,
      currentStage: initialStage,
    }));

    // Always sync planner tabs: restore from loaded workflow, or seed a default
    // so the Planner is never empty (a "Run 1" snapshot of current canvas params).
    const plannerData = workflowJson.metadata?.gui?.planner?.tabs;
    if (Array.isArray(plannerData) && plannerData.length > 0) {
      get().setPlannerTabs(plannerData);
    } else {
      get().setPlannerTabs([]);   // resets nextTabCounter to 1, clears stale state
      get().addPlannerTab();      // seeds "Run 1" with default snapshot, sets active
    }
  },

  // Export workflow to JSON (V2-only)
  exportWorkflow: () => {
    const state = get();
    const { workflow, stageNodes, stageEdges } = state;

    // The stored `subworkflows[*].execution_order` is a stale cache from the
    // last load/export — it is NOT kept in sync as nodes are added or deleted
    // on the canvas. Export regenerates it from the live graph below
    // (findReachableNodes), so a node deleted on the canvas still lingers in the
    // stored order until then. Validating that stale cache would crash export on
    // a node the user already removed ("references unknown node ID ..."). Prune
    // each order to the IDs that actually exist on the canvas before validating;
    // the canvas is the source of truth for what gets exported.
    const validationWorkflow = {
      ...workflow,
      subworkflows: Object.fromEntries(
        Object.entries(workflow.subworkflows).map(([name, sw]) => {
          const liveIds = new Set((stageNodes[name] || []).map((n) => n.id));
          const order = sw.execution_order || [];
          const prunedOrder = order.filter((id) => liveIds.has(id));
          return [name, prunedOrder.length === order.length ? sw : { ...sw, execution_order: prunedOrder }];
        })
      ),
    };

    // Comprehensive validation before export
    const validationResult = validateWorkflow(validationWorkflow, stageNodes);

    if (!validationResult.valid) {
      const errorMessage = 'Workflow validation failed:\n\n' + validationResult.errors.join('\n');
      console.error('[EXPORT] Validation errors:', validationResult.errors);
      alert(errorMessage);
      throw new Error(errorMessage);
    }
    if (validationResult.warnings?.length > 0) {
      console.warn('[EXPORT] Validation warnings:', validationResult.warnings);
    }

    // Rebuild subworkflows (and synthesize `main`) from the LIVE canvas graph.
    // This is the single shared assembly path — the read-only Overview canvas
    // uses the same function, so what you see assembled is exactly what exports.
    const subworkflows = assembleSubworkflowsFromStages(workflow, stageNodes, stageEdges);

    // ABM-derived locals for the exported metadata block below.
    const guiMeta = workflow.metadata?.gui || {};
    const agentKinds = guiMeta.agent_kinds || [];
    const resourceKinds = guiMeta.resource_kinds || [];
    const worldMeta = guiMeta.world || {};
    const processingMeta = guiMeta.processing || {};
    const schedulerMeta = guiMeta.scheduler || {};
    const initSeqMeta = guiMeta.init_sequence || { subworkflow: INIT_SEQUENCE_NAME };
    const hasAbmContent = agentKinds.length > 0 || resourceKinds.length > 0 || worldMeta.subworkflow ||
      (worldMeta.behavior_subworkflows || []).length > 0 ||
      (processingMeta.behavior_subworkflows || []).length > 0 ||
      subworkflows[schedulerMeta.subworkflow || '__scheduler__'];

    // Make library paths relative to workflow file
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

    // Always emit ABM fields and mark synthesis. Phase 14B: `subworkflow_kinds`
    // is intentionally omitted — it is derived at load time from the ABM
    // metadata below, so persisting it would create a redundant second source
    // of truth that could silently disagree.
    const { subworkflow_kinds: _droppedKinds, ...guiWithoutKinds } = exportedMetadata.gui || {};
    exportedMetadata.gui = {
      ...guiWithoutKinds,
      agent_kinds: agentKinds,
      world: worldMeta,
      init_sequence: initSeqMeta,
      scheduler: schedulerMeta,
      processing: processingMeta,
      main_is_synthesized: hasAbmContent,
      user_functions: guiMeta.user_functions || [],
    };

    // Include planner tabs in exported metadata
    const { plannerTabs } = state;
    if (plannerTabs && plannerTabs.length > 0) {
      exportedMetadata.gui = {
        ...exportedMetadata.gui,
        planner: {
          tabs: plannerTabs.map((t) => ({
            id: t.id,
            name: t.name,
            enabled: t.enabled,
            parameterOverrides: t.parameterOverrides,
          })),
        },
      };
    }

    // Embed original workflow file path so the engine can resolve relative paths
    // even when the workflow is saved to a temp file by the GUI
    if (state.workflowFilePath) {
      exportedMetadata.workflow_source_path = state.workflowFilePath;
    }

    return {
      version: '2.0',
      name: workflow.name,
      description: workflow.description,
      // Preserve the kernel selector and its config. Without these a workflow
      // that declares `kernel: "physicell"` is exported as plain biophysics, so
      // the engine never dispatches to the facade backend (it just runs the
      // empty Python stage loop). Omitted entirely for default biophysics
      // workflows, which carry no kernel field.
      ...(workflow.kernel ? { kernel: workflow.kernel } : {}),
      ...(workflow.kernel_config ? { kernel_config: workflow.kernel_config } : {}),
      // Run-level RNG seed for reproducible random iteration order. `!= null`
      // keeps an explicit 0 (which means "fresh entropy"); omitted when unset
      // so the engine applies its default (42).
      ...(workflow.seed != null ? { seed: workflow.seed } : {}),
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
        ...(node.data.contract ? { contract: node.data.contract } : {}),
        ...(node.data.functionFile ? { function_file: node.data.functionFile } : {})
      }));

    // Build subworkflow_calls array from nodes
    const subworkflow_calls = nodes
      .filter(node => node.type === 'subworkflowCall')
      .map((node) => {
        const forEach = node.data.forEach || deriveForEachForBehavior(workflow.metadata?.gui || {}, node.data.subworkflowName);
        return {
          id: node.id,
          subworkflow_name: node.data.subworkflowName,
          iterations: node.data.iterations || 1,
          ...(forEach ? { for_each: forEach } : {}),
          enabled: node.data.enabled !== false,
          verbose: node.data.verbose || false,
          description: node.data.description || '',
          parameters: node.data.parameters || {},
          context_mapping: node.data.contextMapping || {},
          parameter_nodes: node.data.parameterNodes || [],
          position: node.position
        };
      });

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
      ...(subworkflow.contract ? { contract: subworkflow.contract } : {}),
      exported_from: workflow.name,
      exported_at: new Date().toISOString(),
      subworkflow: {
        description: subworkflow.description || '',
        enabled: subworkflow.enabled !== false,
        deletable: subworkflow.deletable !== false,
        ...(subworkflow.contract ? { contract: subworkflow.contract } : {}),
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

    // User-facing names start with a letter; system subworkflows use a dunder
    // convention (e.g. '__scheduler__', '__init_sequence__') and are exempt.
    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name) && !/^__[a-zA-Z][a-zA-Z0-9_]*__$/.test(name)) {
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
          contract: func.contract || null,
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
        nodeData.data.targetParam = param.target_param ?? param.targetParam ?? 'items';
      } else if (param.type === 'dictParameterNode') {
        nodeData.data.entries = param.entries || [];
        nodeData.data.targetParam = param.target_param ?? param.targetParam;
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
            input_parameters: swData.input_parameters || [],
            ...(swData.contract ? { contract: swData.contract } : {})
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

        // Phase 13: auto-attach ABM-kind behaviors to the appropriate group
        // so the user doesn't have to wire them up manually after import.
        const targetAgentKind = options.attachToAgentKind || null;
        get()._attachImportedToAbm(targetName, kind, targetAgentKind);
      } else {
        results.failed.push({ name: originalName, error: 'Import failed' });
      }
    }

    console.log('[STORE] Import results:', results);
    return results;
  },

  /**
   * Phase 13: hook a freshly imported subworkflow into the right ABM group
   * based on its kind. Idempotent.
   */
  _attachImportedToAbm: (name, kind, targetAgentKind = null) => {
    set((state) => {
      const gui = state.workflow.metadata?.gui;
      if (!gui) return state;

      // World behavior (per-step collective)
      if (kind === 'world_behavior') {
        const world = gui.world || { subworkflow: null, behavior_subworkflows: [] };
        const behaviors = world.behavior_subworkflows || [];
        if (behaviors.includes(name)) return state;
        return {
          workflow: {
            ...state.workflow,
            metadata: {
              ...state.workflow.metadata,
              gui: {
                ...gui,
                world: {
                  ...world,
                  behavior_subworkflows: [...behaviors, name],
                },
              },
            },
          },
        };
      }

      // World init (the one world-setup subworkflow)
      if (kind === 'world') {
        const world = gui.world || { subworkflow: null, behavior_subworkflows: [] };
        return {
          workflow: {
            ...state.workflow,
            metadata: {
              ...state.workflow.metadata,
              gui: {
                ...gui,
                world: { ...world, subworkflow: name },
              },
            },
          },
        };
      }

      // Processing behavior
      if (kind === 'processing_behavior') {
        const proc = gui.processing || { behavior_subworkflows: [] };
        if (proc.behavior_subworkflows.includes(name)) return state;
        return {
          workflow: {
            ...state.workflow,
            metadata: {
              ...state.workflow.metadata,
              gui: {
                ...gui,
                processing: {
                  ...proc,
                  behavior_subworkflows: [...proc.behavior_subworkflows, name],
                },
              },
            },
          },
        };
      }

      // Agent behavior / agent init — needs a target agent kind. If the caller
      // did not specify one, attach to the first existing kind, or skip silently
      // (the user can attach manually from the Agents tab).
      if (kind === 'agent_behavior' || kind === 'agent_init') {
        const kinds = gui.agent_kinds || [];
        if (kinds.length === 0) return state;

        const targetName = targetAgentKind || kinds[0].name;
        const newKinds = kinds.map((k) => {
          if (k.name !== targetName) return k;
          if (kind === 'agent_init') return { ...k, init_subworkflow: name };
          if (k.behavior_subworkflows.includes(name)) return k;
          return { ...k, behavior_subworkflows: [...k.behavior_subworkflows, name] };
        });

        return {
          workflow: {
            ...state.workflow,
            metadata: {
              ...state.workflow.metadata,
              gui: { ...gui, agent_kinds: newKinds },
            },
          },
        };
      }

      return state;
    });
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
