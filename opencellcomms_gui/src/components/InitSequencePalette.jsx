import { Users, Boxes, Globe, Plus, Check } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import { INIT_SEQUENCE_NAME } from '../store/subworkflowKinds';
import './InitSequencePalette.css';

const InitSequencePalette = () => {
  const { workflow, addToInitSequence } = useWorkflowStore();

  const agentKinds = workflow.metadata?.gui?.agent_kinds || [];
  const resourceKinds = workflow.metadata?.gui?.resource_kinds || [];
  const worldSw = workflow.metadata?.gui?.world?.subworkflow;
  const calls = workflow.subworkflows?.[INIT_SEQUENCE_NAME]?.subworkflow_calls || [];
  const scheduled = new Set(calls.map((c) => c.subworkflow_name));

  const hasContent = !!worldSw || agentKinds.some((k) => k.init_subworkflow) || resourceKinds.some((k) => k.init_subworkflow);

  return (
    <div className="init-sequence-palette">
      <div className="init-sequence-palette-title">Available Inits</div>

      {worldSw && (
        <section className="initseq-section">
          <div className="initseq-section-header">
            <Globe size={13} />
            <span>World</span>
          </div>
          <InitItem
            name={worldSw}
            color="#10b981"
            scheduled={scheduled.has(worldSw)}
            onAdd={() => addToInitSequence(worldSw)}
          />
        </section>
      )}

      {agentKinds.map((kind) => (
        kind.init_subworkflow && (
          <section key={kind.name} className="initseq-section">
            <div className="initseq-section-header agent">
              <Users size={13} />
              <span>{kind.name}</span>
            </div>
            <InitItem
              name={kind.init_subworkflow}
              color="#3b82f6"
              scheduled={scheduled.has(kind.init_subworkflow)}
              onAdd={() => addToInitSequence(kind.init_subworkflow)}
            />
          </section>
        )
      ))}

      {resourceKinds.map((kind) => (
        kind.init_subworkflow && (
          <section key={kind.name} className="initseq-section">
            <div className="initseq-section-header">
              <Boxes size={13} />
              <span>{kind.name}</span>
            </div>
            <InitItem
              name={kind.init_subworkflow}
              color="#10b981"
              scheduled={scheduled.has(kind.init_subworkflow)}
              onAdd={() => addToInitSequence(kind.init_subworkflow)}
            />
          </section>
        )
      ))}

      {!hasContent && (
        <div className="initseq-empty">
          Define init canvases in the Agents and World tabs first.
        </div>
      )}
    </div>
  );
};

const InitItem = ({ name, color, scheduled, onAdd }) => (
  <div
    className={`initseq-item ${scheduled ? 'scheduled' : ''}`}
    style={{ '--color': color }}
  >
    <span className="initseq-item-dot" style={{ background: color }} />
    <span className="initseq-item-name">{name}</span>
    {scheduled ? (
      <Check size={13} className="initseq-item-check" />
    ) : (
      <button
        className="initseq-item-add"
        onClick={onAdd}
        title={`Add ${name} to init sequence`}
      >
        <Plus size={13} />
      </button>
    )}
  </div>
);

export default InitSequencePalette;
