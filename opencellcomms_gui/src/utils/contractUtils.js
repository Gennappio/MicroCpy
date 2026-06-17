import {
  KINDS,
  PROCESS_PHASE_LABELS,
  defaultContractForKind,
} from '../store/subworkflowKinds';

export const CONTRACT_PHASE_LABELS = PROCESS_PHASE_LABELS;

export const expectedPhaseForKind = (kind, canvasContract = null) => {
  if (canvasContract?.phase) return canvasContract.phase;

  switch (kind) {
    case KINDS.AGENT_INIT:
    case KINDS.RESOURCE_INIT:
    case KINDS.ENV_INIT:
    case KINDS.SPACE:
      return 'initialization';
    case KINDS.AGENT_BEHAVIOR:
      return 'agent_behavior';
    case KINDS.RESOURCE_BEHAVIOR:
      return 'resource_behavior';
    case KINDS.PROCESSING_BEHAVIOR:
      return 'reporting';
    case KINDS.ENV_BEHAVIOR:
      return null;
    default:
      return null;
  }
};

export const inferredContractForCanvas = (currentKind, canvasContract = null) => {
  const contract = canvasContract || defaultContractForKind(currentKind);
  if (!contract) return null;
  return { ...contract, inferred: true };
};

export const inferContractFromCategory = (category, currentKind, canvasContract = null) => {
  const normalized = String(category || '').toLowerCase();

  if (normalized === 'finalization' || normalized === 'output') {
    return { phase: 'reporting', reads: [], writes: [], emits: [], inferred: true };
  }
  if (normalized === 'initialization') {
    return { phase: 'initialization', reads: [], writes: [], emits: [], inferred: true };
  }
  if (normalized === 'intracellular') {
    return { phase: 'agent_behavior', reads: [], writes: [], emits: [], inferred: true };
  }
  if (normalized === 'diffusion' || normalized === 'microenvironment') {
    const expected = expectedPhaseForKind(currentKind, canvasContract);
    return {
      phase: expected === 'coupling' ? 'coupling' : 'resource_behavior',
      reads: [],
      writes: [],
      emits: [],
      inferred: true,
    };
  }
  if (normalized === 'intercellular') {
    return { phase: 'coupling', reads: [], writes: [], emits: [], inferred: true };
  }

  return inferredContractForCanvas(currentKind, canvasContract);
};

export const contractForFunction = (meta, userFn, currentKind, canvasContract = null) => {
  if (meta?.contract) return { ...meta.contract, inferred: false };
  if (userFn?.contract) return { ...userFn.contract, inferred: false };
  return inferContractFromCategory(meta?.category || userFn?.category, currentKind, canvasContract);
};

export const contractForSubworkflow = (subworkflow, kind) => {
  if (subworkflow?.contract) return { ...subworkflow.contract, inferred: false };
  return inferredContractForCanvas(kind);
};

export const processRoleForSubworkflow = (subworkflow, kind) => {
  const contract = contractForSubworkflow(subworkflow, kind);
  const phase = contract?.phase || null;
  return {
    contract,
    phase,
    label: CONTRACT_PHASE_LABELS[phase] || phase || 'Unspecified',
    inferred: !!contract?.inferred,
  };
};

export const compatibilityForContract = (contract, currentKind, canvasContract = null) => {
  if (!contract) {
    return { level: 'unknown', label: 'No contract', reason: 'No contract metadata is available yet.' };
  }

  const expectedPhase = expectedPhaseForKind(currentKind, canvasContract);
  if (!expectedPhase) {
    return { level: 'neutral', label: 'Contracted', reason: 'This canvas accepts multiple process phases.' };
  }

  if (contract.phase === expectedPhase) {
    return {
      level: contract.inferred ? 'inferred' : 'match',
      label: contract.inferred ? 'Inferred match' : 'Contract match',
      reason: `Matches ${CONTRACT_PHASE_LABELS[expectedPhase] || expectedPhase}.`,
    };
  }

  if (contract.inferred) {
    return {
      level: 'soft-mismatch',
      label: 'Check phase',
      reason: `Inferred ${CONTRACT_PHASE_LABELS[contract.phase] || contract.phase}, expected ${CONTRACT_PHASE_LABELS[expectedPhase] || expectedPhase}.`,
    };
  }

  return {
    level: 'mismatch',
    label: 'Phase mismatch',
    reason: `Declares ${CONTRACT_PHASE_LABELS[contract.phase] || contract.phase}, expected ${CONTRACT_PHASE_LABELS[expectedPhase] || expectedPhase}.`,
  };
};

export const formatContractList = (items) => {
  if (!Array.isArray(items) || items.length === 0) return 'None';
  return items.join(', ');
};
