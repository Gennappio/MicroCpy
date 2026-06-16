import { KINDS } from '../store/subworkflowKinds';

export const CONTRACT_PHASE_LABELS = {
  initialization: 'Initialization',
  agent_behavior: 'Agent behavior',
  resource_behavior: 'Resource behavior',
  space_behavior: 'Space behavior',
  coupling: 'Coupling',
  reconciliation: 'Reconciliation',
  reporting: 'Reporting',
};

export const expectedPhaseForKind = (kind) => {
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

export const inferContractFromCategory = (category, currentKind) => {
  const normalized = String(category || '').toLowerCase();
  const expected = expectedPhaseForKind(currentKind);

  if (expected) {
    return {
      phase: expected,
      reads: [],
      writes: [],
      emits: [],
      inferred: true,
    };
  }

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
    return { phase: 'resource_behavior', reads: [], writes: [], emits: [], inferred: true };
  }
  if (normalized === 'intercellular') {
    return { phase: 'coupling', reads: [], writes: [], emits: [], inferred: true };
  }

  return null;
};

export const contractForFunction = (meta, userFn, currentKind) => {
  if (meta?.contract) return { ...meta.contract, inferred: false };
  if (userFn?.contract) return { ...userFn.contract, inferred: false };
  return inferContractFromCategory(meta?.category || userFn?.category, currentKind);
};

export const compatibilityForContract = (contract, currentKind) => {
  if (!contract) {
    return { level: 'unknown', label: 'No contract', reason: 'No contract metadata is available yet.' };
  }

  const expectedPhase = expectedPhaseForKind(currentKind);
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
