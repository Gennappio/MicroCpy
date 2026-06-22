/**
 * Canonical reconciliation pipeline — the single source of truth for the
 * ordered, mechanical commit steps the engine runs inside `apply_reconciliation`.
 *
 * This MIRRORS, in order, the body of:
 *   opencellcomms_engine/src/workflow/functions/reconciliation/apply_reconciliation.py
 *
 * The Overview canvas renders these as locked, read-only "system" nodes so a
 * scientist can SEE what the reconciliation node does (and in what order) without
 * being able to edit the plumbing. The order is load-bearing: resource deltas
 * commit before consumption can read availability; moves resolve before agents
 * consume at their new tile; deaths are culled last.
 *
 * NOTE (prototype): this list is hand-kept in sync with the Python source. The
 * intended v2 is to have the engine serve this list from the actual handler
 * registry so the GUI and the executor cannot drift. Until then, treat this file
 * and apply_reconciliation.py as a pair that must change together.
 */

export const RECONCILIATION_SOURCE = 'engine · apply_reconciliation.py';

export const RECONCILIATION_STEPS = [
  {
    id: 'resource_delta',
    label: 'Apply resource deltas',
    intent: 'resource_delta',
    description:
      'Commit queued source/sink terms onto resource fields, then apply sources.',
  },
  {
    id: 'move',
    label: 'Move agents',
    intent: 'move',
    description:
      "Relocate each agent to its requested tile (normalized to the world topology).",
  },
  {
    id: 'consume_resource',
    label: 'Consume resources',
    intent: 'consume_resource',
    description:
      "Transfer available resource at the agent's tile into an agent state variable.",
  },
  {
    id: 'add_agent',
    label: 'Add agents',
    intent: 'add_agent',
    description: 'Spawn the agents requested by birth intents.',
  },
  {
    id: 'remove_agent',
    label: 'Remove agents',
    intent: 'remove_agent',
    description: 'Cull agents whose removal was explicitly requested.',
  },
  {
    id: 'cull_dead',
    label: 'Cull dead',
    intent: null,
    // The one genuine policy knob in an otherwise mechanical pipeline:
    // lock the wiring, expose the parameter.
    param: 'cull_dead',
    description:
      'Remove agents flagged dead by behaviours. Gated by the cull_dead parameter.',
  },
];

/** Function name whose presence on a behavior canvas means "this is where the
 *  engine reconciliation pipeline runs", so the Overview should expand it. */
export const RECONCILIATION_FUNCTION = 'apply_reconciliation';
