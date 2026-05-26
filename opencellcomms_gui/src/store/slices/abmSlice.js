import { KINDS, SCHEDULER_NAME, INIT_SEQUENCE_NAME } from '../subworkflowKinds';
import { withDerivedKinds } from '../computeSubworkflowKinds';

const makeSubworkflow = (name, description, kind) => ({
  description,
  enabled: true,
  deletable: true,
  kind,
  controller: {
    id: `controller-${name}`,
    type: 'initNode',
    label: `${name.toUpperCase()} CONTROLLER`,
    position: { x: 100, y: 100 },
    number_of_steps: 1,
  },
  functions: [],
  subworkflow_calls: [],
  parameters: [],
  execution_order: [],
  input_parameters: [],
});

const makeControllerNode = (name) => ({
  id: `controller-${name}`,
  type: 'initNode',
  position: { x: 100, y: 100 },
  data: { label: `${name.toUpperCase()} CONTROLLER`, numberOfSteps: 1 },
  deletable: false,
});

export const createAbmSlice = (set, get) => ({

  // ── Agent kinds ──────────────────────────────────────────────────────────

  addAgentKind: (name) => {
    const initName = `${name}_init`;
    set((state) => {
      if (state.workflow.metadata.gui.agent_kinds.find((k) => k.name === name)) return state;
      const initSw = makeSubworkflow(initName, `Initialization for ${name}`, KINDS.AGENT_INIT);
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            agent_kinds: [
              ...state.workflow.metadata.gui.agent_kinds,
              { name, init_subworkflow: initName, behavior_subworkflows: [] },
            ],
          },
        },
        subworkflows: {
          ...state.workflow.subworkflows,
          [initName]: initSw,
        },
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: { ...state.stageNodes, [initName]: [makeControllerNode(initName)] },
        stageEdges: { ...state.stageEdges, [initName]: [] },
      };
    });
  },

  removeAgentKind: (name) => {
    set((state) => {
      const kind = state.workflow.metadata.gui.agent_kinds.find((k) => k.name === name);
      if (!kind) return state;

      const toRemove = new Set([kind.init_subworkflow, ...kind.behavior_subworkflows]);
      const newSubworkflows = { ...state.workflow.subworkflows };
      const newNodes = { ...state.stageNodes };
      const newEdges = { ...state.stageEdges };
      toRemove.forEach((n) => { delete newSubworkflows[n]; delete newNodes[n]; delete newEdges[n]; });

      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            agent_kinds: state.workflow.metadata.gui.agent_kinds.filter((k) => k.name !== name),
          },
        },
        subworkflows: newSubworkflows,
      };

      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: newNodes,
        stageEdges: newEdges,
        currentStage: toRemove.has(state.currentStage) ? SCHEDULER_NAME : state.currentStage,
      };
    });
  },

  addAgentBehavior: (kindName, behaviorName) => {
    set((state) => {
      if (state.workflow.subworkflows[behaviorName]) return state;
      const sw = makeSubworkflow(behaviorName, `${kindName} behavior: ${behaviorName}`, KINDS.AGENT_BEHAVIOR);
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            agent_kinds: state.workflow.metadata.gui.agent_kinds.map((k) =>
              k.name === kindName
                ? { ...k, behavior_subworkflows: [...k.behavior_subworkflows, behaviorName] }
                : k
            ),
          },
        },
        subworkflows: { ...state.workflow.subworkflows, [behaviorName]: sw },
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: { ...state.stageNodes, [behaviorName]: [makeControllerNode(behaviorName)] },
        stageEdges: { ...state.stageEdges, [behaviorName]: [] },
      };
    });
  },

  removeAgentBehavior: (kindName, behaviorName) => {
    set((state) => {
      const { [behaviorName]: _sw, ...newSubworkflows } = state.workflow.subworkflows;
      const { [behaviorName]: _n, ...newNodes } = state.stageNodes;
      const { [behaviorName]: _e, ...newEdges } = state.stageEdges;
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            agent_kinds: state.workflow.metadata.gui.agent_kinds.map((k) =>
              k.name === kindName
                ? { ...k, behavior_subworkflows: k.behavior_subworkflows.filter((b) => b !== behaviorName) }
                : k
            ),
          },
        },
        subworkflows: newSubworkflows,
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: newNodes,
        stageEdges: newEdges,
        currentStage: state.currentStage === behaviorName ? SCHEDULER_NAME : state.currentStage,
      };
    });
  },

  // ── Environment ───────────────────────────────────────────────────────────

  ensureEnvironmentInit: () => {
    set((state) => {
      const existing = state.workflow.metadata.gui.environment.init_subworkflow;
      if (existing) return state;
      const name = 'environment_init';
      const sw = makeSubworkflow(name, 'Environment initialization', KINDS.ENV_INIT);
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            environment: { ...state.workflow.metadata.gui.environment, init_subworkflow: name },
          },
        },
        subworkflows: { ...state.workflow.subworkflows, [name]: sw },
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: { ...state.stageNodes, [name]: [makeControllerNode(name)] },
        stageEdges: { ...state.stageEdges, [name]: [] },
      };
    });
  },

  addEnvironmentBehavior: (behaviorName) => {
    set((state) => {
      if (state.workflow.subworkflows[behaviorName]) return state;
      const sw = makeSubworkflow(behaviorName, `Environment behavior: ${behaviorName}`, KINDS.ENV_BEHAVIOR);
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            environment: {
              ...state.workflow.metadata.gui.environment,
              behavior_subworkflows: [...state.workflow.metadata.gui.environment.behavior_subworkflows, behaviorName],
            },
          },
        },
        subworkflows: { ...state.workflow.subworkflows, [behaviorName]: sw },
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: { ...state.stageNodes, [behaviorName]: [makeControllerNode(behaviorName)] },
        stageEdges: { ...state.stageEdges, [behaviorName]: [] },
      };
    });
  },

  removeEnvironmentBehavior: (behaviorName) => {
    set((state) => {
      const { [behaviorName]: _sw, ...newSubworkflows } = state.workflow.subworkflows;
      const { [behaviorName]: _n, ...newNodes } = state.stageNodes;
      const { [behaviorName]: _e, ...newEdges } = state.stageEdges;
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            environment: {
              ...state.workflow.metadata.gui.environment,
              behavior_subworkflows: state.workflow.metadata.gui.environment.behavior_subworkflows.filter((b) => b !== behaviorName),
            },
          },
        },
        subworkflows: newSubworkflows,
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: newNodes,
        stageEdges: newEdges,
        currentStage: state.currentStage === behaviorName ? SCHEDULER_NAME : state.currentStage,
      };
    });
  },

  // ── Processing ────────────────────────────────────────────────────────────

  addProcessingBehavior: (behaviorName) => {
    set((state) => {
      if (state.workflow.subworkflows[behaviorName]) return state;
      const sw = makeSubworkflow(behaviorName, `Processing: ${behaviorName}`, KINDS.PROCESSING_BEHAVIOR);
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            processing: {
              ...state.workflow.metadata.gui.processing,
              behavior_subworkflows: [...state.workflow.metadata.gui.processing.behavior_subworkflows, behaviorName],
            },
          },
        },
        subworkflows: { ...state.workflow.subworkflows, [behaviorName]: sw },
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: { ...state.stageNodes, [behaviorName]: [makeControllerNode(behaviorName)] },
        stageEdges: { ...state.stageEdges, [behaviorName]: [] },
      };
    });
  },

  removeProcessingBehavior: (behaviorName) => {
    set((state) => {
      const { [behaviorName]: _sw, ...newSubworkflows } = state.workflow.subworkflows;
      const { [behaviorName]: _n, ...newNodes } = state.stageNodes;
      const { [behaviorName]: _e, ...newEdges } = state.stageEdges;
      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            processing: {
              ...state.workflow.metadata.gui.processing,
              behavior_subworkflows: state.workflow.metadata.gui.processing.behavior_subworkflows.filter((b) => b !== behaviorName),
            },
          },
        },
        subworkflows: newSubworkflows,
      };
      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: newNodes,
        stageEdges: newEdges,
        currentStage: state.currentStage === behaviorName ? SCHEDULER_NAME : state.currentStage,
      };
    });
  },

  // ── Scheduler ─────────────────────────────────────────────────────────────

  addToScheduler: (behaviorName) => {
    set((state) => {
      const scheduler = state.workflow.subworkflows[SCHEDULER_NAME];
      const alreadyPresent = (scheduler.subworkflow_calls || []).some((c) => c.subworkflow_name === behaviorName);
      if (alreadyPresent) return state;

      const callId = `sched-call-${behaviorName}-${Date.now()}`;
      const newCall = {
        id: callId,
        type: 'subworkflow_call',
        subworkflow_name: behaviorName,
        iterations: 1,
        parameters: {},
        enabled: true,
        position: { x: 400, y: 100 + (scheduler.subworkflow_calls || []).length * 120 },
        description: behaviorName,
        parameter_nodes: [],
      };

      const newCallNode = {
        id: callId,
        type: 'subworkflowCall',
        position: newCall.position,
        data: {
          label: behaviorName,
          subworkflowName: behaviorName,
          iterations: 1,
          enabled: true,
          description: behaviorName,
        },
      };

      const existingNodes = state.stageNodes[SCHEDULER_NAME] || [];
      const existingOrder = scheduler.execution_order || [];

      return {
        workflow: {
          ...state.workflow,
          subworkflows: {
            ...state.workflow.subworkflows,
            [SCHEDULER_NAME]: {
              ...scheduler,
              subworkflow_calls: [...(scheduler.subworkflow_calls || []), newCall],
              execution_order: [...existingOrder, callId],
            },
          },
        },
        stageNodes: {
          ...state.stageNodes,
          [SCHEDULER_NAME]: [...existingNodes, newCallNode],
        },
      };
    });
  },

  removeFromScheduler: (nodeId) => {
    set((state) => {
      const scheduler = state.workflow.subworkflows[SCHEDULER_NAME];
      return {
        workflow: {
          ...state.workflow,
          subworkflows: {
            ...state.workflow.subworkflows,
            [SCHEDULER_NAME]: {
              ...scheduler,
              subworkflow_calls: (scheduler.subworkflow_calls || []).filter((c) => c.id !== nodeId),
              execution_order: (scheduler.execution_order || []).filter((id) => id !== nodeId),
            },
          },
        },
        stageNodes: {
          ...state.stageNodes,
          [SCHEDULER_NAME]: (state.stageNodes[SCHEDULER_NAME] || []).filter((n) => n.id !== nodeId),
        },
      };
    });
  },

  // ── Initialization sequence (Phase 14C) ───────────────────────────────────

  // Idempotently create the __init_sequence__ subworkflow + register it in
  // metadata.gui.init_sequence. Safe to call from load paths and default state.
  ensureInitSequence: () => {
    set((state) => {
      const hasSubworkflow = !!state.workflow.subworkflows[INIT_SEQUENCE_NAME];
      const hasMeta = state.workflow.metadata?.gui?.init_sequence?.subworkflow === INIT_SEQUENCE_NAME;
      if (hasSubworkflow && hasMeta) return state;

      const initSeqSw = hasSubworkflow ? state.workflow.subworkflows[INIT_SEQUENCE_NAME] : {
        description: 'Initialization order — drag init subworkflows here',
        enabled: true,
        deletable: false,
        controller: {
          id: `controller-${INIT_SEQUENCE_NAME}`,
          type: 'initNode',
          label: 'INIT SEQUENCE',
          position: { x: 100, y: 100 },
          number_of_steps: 1,
        },
        functions: [],
        subworkflow_calls: [],
        parameters: [],
        execution_order: [],
        input_parameters: [],
      };

      const newWorkflow = {
        ...state.workflow,
        metadata: {
          ...state.workflow.metadata,
          gui: {
            ...state.workflow.metadata.gui,
            init_sequence: { subworkflow: INIT_SEQUENCE_NAME },
          },
        },
        subworkflows: {
          ...state.workflow.subworkflows,
          [INIT_SEQUENCE_NAME]: initSeqSw,
        },
      };

      return {
        workflow: withDerivedKinds(newWorkflow),
        stageNodes: {
          ...state.stageNodes,
          [INIT_SEQUENCE_NAME]: hasSubworkflow ? state.stageNodes[INIT_SEQUENCE_NAME] : [
            {
              id: `controller-${INIT_SEQUENCE_NAME}`,
              type: 'initNode',
              position: { x: 100, y: 100 },
              data: { label: 'INIT SEQUENCE', numberOfSteps: 1 },
              deletable: false,
            },
          ],
        },
        stageEdges: {
          ...state.stageEdges,
          [INIT_SEQUENCE_NAME]: state.stageEdges[INIT_SEQUENCE_NAME] || [],
        },
      };
    });
  },

  addToInitSequence: (initName) => {
    set((state) => {
      const seq = state.workflow.subworkflows[INIT_SEQUENCE_NAME];
      if (!seq) return state;
      const alreadyPresent = (seq.subworkflow_calls || []).some((c) => c.subworkflow_name === initName);
      if (alreadyPresent) return state;

      const callId = `init-call-${initName}-${Date.now()}`;
      const newCall = {
        id: callId,
        type: 'subworkflow_call',
        subworkflow_name: initName,
        iterations: 1,
        parameters: {},
        enabled: true,
        position: { x: 400, y: 100 + (seq.subworkflow_calls || []).length * 120 },
        description: initName,
        parameter_nodes: [],
      };

      const newCallNode = {
        id: callId,
        type: 'subworkflowCall',
        position: newCall.position,
        data: {
          label: initName,
          subworkflowName: initName,
          iterations: 1,
          enabled: true,
          description: initName,
        },
      };

      const existingNodes = state.stageNodes[INIT_SEQUENCE_NAME] || [];
      const existingOrder = seq.execution_order || [];

      return {
        workflow: {
          ...state.workflow,
          subworkflows: {
            ...state.workflow.subworkflows,
            [INIT_SEQUENCE_NAME]: {
              ...seq,
              subworkflow_calls: [...(seq.subworkflow_calls || []), newCall],
              execution_order: [...existingOrder, callId],
            },
          },
        },
        stageNodes: {
          ...state.stageNodes,
          [INIT_SEQUENCE_NAME]: [...existingNodes, newCallNode],
        },
      };
    });
  },

  removeFromInitSequence: (nodeId) => {
    set((state) => {
      const seq = state.workflow.subworkflows[INIT_SEQUENCE_NAME];
      if (!seq) return state;
      return {
        workflow: {
          ...state.workflow,
          subworkflows: {
            ...state.workflow.subworkflows,
            [INIT_SEQUENCE_NAME]: {
              ...seq,
              subworkflow_calls: (seq.subworkflow_calls || []).filter((c) => c.id !== nodeId),
              execution_order: (seq.execution_order || []).filter((id) => id !== nodeId),
            },
          },
        },
        stageNodes: {
          ...state.stageNodes,
          [INIT_SEQUENCE_NAME]: (state.stageNodes[INIT_SEQUENCE_NAME] || []).filter((n) => n.id !== nodeId),
        },
      };
    });
  },
});
