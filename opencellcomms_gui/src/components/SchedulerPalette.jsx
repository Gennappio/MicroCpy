import { Users, Boxes, Globe, Plus, Check } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import { SCHEDULER_NAME, INIT_KINDS } from '../store/subworkflowKinds';
import './SchedulerPalette.css';

const SchedulerPalette = () => {
  const { workflow, addToScheduler } = useWorkflowStore();

  const agentKinds = workflow.metadata?.gui?.agent_kinds || [];
  const resourceKinds = workflow.metadata?.gui?.resource_kinds || [];
  const worldMeta = workflow.metadata?.gui?.world || {};
  const kindsMap = workflow.metadata?.gui?.subworkflow_kinds || {};
  const schedulerCalls = workflow.subworkflows?.[SCHEDULER_NAME]?.subworkflow_calls || [];
  const scheduled = new Set(schedulerCalls.map((c) => c.subworkflow_name));

  // Phase 14C: defensive — never expose init kinds in the scheduler palette.
  // Inits belong in the Initialization tab and run exactly once before the loop.
  const isNotInit = (name) => !INIT_KINDS.has(kindsMap[name]);
  const worldBehaviors = (worldMeta.behavior_subworkflows || []).filter(isNotInit);

  return (
    <div className="scheduler-palette">
      <div className="scheduler-palette-title">Available Behaviors</div>

      {/* World behaviors */}
      {worldBehaviors.length > 0 && (
        <section className="sched-section">
          <div className="sched-section-header env">
            <Globe size={13} />
            <span>World</span>
          </div>
          {worldBehaviors.map((name) => (
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
      {agentKinds.map((kind) => {
        const behaviors = (kind.behavior_subworkflows || []).filter(isNotInit);
        if (behaviors.length === 0) return null;
        return (
          <section key={kind.name} className="sched-section">
            <div className="sched-section-header agent">
              <Users size={13} />
              <span>{kind.name}</span>
            </div>
            {behaviors.map((name) => (
              <BehaviorItem
                key={name}
                name={name}
                color="#3b82f6"
                scheduled={scheduled.has(name)}
                onAdd={() => addToScheduler(name)}
              />
            ))}
          </section>
        );
      })}

      {/* Per-resource step behaviors */}
      {resourceKinds.map((kind) => {
        const behaviors = (kind.behavior_subworkflows || []).filter(isNotInit);
        if (behaviors.length === 0) return null;
        return (
          <section key={kind.name} className="sched-section">
            <div className="sched-section-header">
              <Boxes size={13} />
              <span>{kind.name}</span>
            </div>
            {behaviors.map((name) => (
              <BehaviorItem
                key={name}
                name={name}
                color="#10b981"
                scheduled={scheduled.has(name)}
                onAdd={() => addToScheduler(name)}
              />
            ))}
          </section>
        );
      })}

      {worldBehaviors.length === 0
        && agentKinds.every((k) => (k.behavior_subworkflows || []).filter(isNotInit).length === 0)
        && resourceKinds.every((k) => (k.behavior_subworkflows || []).filter(isNotInit).length === 0) && (
        <div className="sched-empty">
          Define behaviors in the Agents or Resources tabs first.
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
