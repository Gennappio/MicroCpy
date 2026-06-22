import { defaultContractForKind } from '../store/subworkflowKinds';

// A contract is the I/O discipline of a behaviour (owner / reads / writes /
// emits). There is no "phase": when and how often a behaviour runs is decided
// by ownership (which tab owns it) and the scheduler's `for_each`, not a tag.

export const inferredContractForCanvas = (currentKind, canvasContract = null) => {
  const contract = canvasContract || defaultContractForKind(currentKind);
  if (!contract) return null;
  return { ...contract, inferred: true };
};

export const contractForFunction = (meta, userFn, currentKind, canvasContract = null) => {
  if (meta?.contract) return { ...meta.contract, inferred: false };
  if (userFn?.contract) return { ...userFn.contract, inferred: false };
  return inferredContractForCanvas(currentKind, canvasContract);
};

export const contractForSubworkflow = (subworkflow, kind) => {
  if (subworkflow?.contract) return { ...subworkflow.contract, inferred: false };
  return inferredContractForCanvas(kind);
};

export const formatContractList = (items) => {
  if (!Array.isArray(items) || items.length === 0) return 'None';
  return items.join(', ');
};
