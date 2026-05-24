import { Users, Globe, Plus, Check } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import { SCHEDULER_NAME } from '../store/subworkflowKinds';
import './SchedulerPalette.css';

const SchedulerPalette = () => {
  const { workflow, addToScheduler } = useWorkflowStore();

  const agentKinds = workflow.metadata?.gui?.agent_kinds || [];
  const envMeta = workflow.metadata?.gui?.environment || {};
  const schedulerCalls = workflow.subworkflows?.[SCHEDULER_NAME]?.subworkflow_calls || [];
  const scheduled = new Set(schedulerCalls.map((c) => c.subworkflow_name));

  const envBehaviors = envMeta.behavior_subworkflows || [];

  return (
    <div className="scheduler-palette">
      <div className="scheduler-palette-title">Available Behaviors</div>

      {/* Environment behaviors */}
      {envBehaviors.length > 0 && (
        <section className="sched-section">
          <div className="sched-section-header env">
            <Globe size={13} />
            <span>Environment</span>
          </div>
          {envBehaviors.map((name) => (
            <BehaviorItem
              key={name}
              name={name}
              color="#10b981"
              scheduled={scheduled.has(name)}
              onAdd={() => addToScheduler(name)}
            />
          ))}
        </section>
      )}

      {/* Per-agent-kind behaviors */}
      {agentKinds.map((kind) => (
        (kind.behavior_subworkflows || []).length > 0 && (
          <section key={kind.name} className="sched-section">
            <div className="sched-section-header agent">
              <Users size={13} />
              <span>{kind.name}</span>
            </div>
            {kind.behavior_subworkflows.map((name) => (
              <BehaviorItem
                key={name}
                name={name}
                color="#3b82f6"
                scheduled={scheduled.has(name)}
                onAdd={() => addToScheduler(name)}
              />
            ))}
          </section>
        )
      ))}

      {envBehaviors.length === 0 && agentKinds.every((k) => (k.behavior_subworkflows || []).length === 0) && (
        <div className="sched-empty">
          Define behaviors in the Agents or Environment tabs first.
        </div>
      )}
    </div>
  );
};

const BehaviorItem = ({ name, color, scheduled, onAdd }) => (
  <div
    className={`sched-behavior-item ${scheduled ? 'scheduled' : ''}`}
    style={{ '--color': color }}
    draggable={!scheduled}
    onDragStart={(e) => {
      e.dataTransfer.setData('application/scheduler-behavior', name);
      e.dataTransfer.effectAllowed = 'copy';
    }}
  >
    <span className="sched-behavior-dot" style={{ background: color }} />
    <span className="sched-behavior-name">{name}</span>
    {scheduled ? (
      <Check size={13} className="sched-behavior-check" />
    ) : (
      <button
        className="sched-behavior-add"
        onClick={onAdd}
        title={`Add ${name} to scheduler`}
      >
        <Plus size={13} />
      </button>
    )}
  </div>
);

export default SchedulerPalette;
