import { Handle, Position } from 'reactflow';
import { Lock, ExternalLink, Repeat, PlayCircle, Sparkles, ArrowDownUp } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './OverviewNode.css';

const HIDDEN_HANDLE = { opacity: 0, pointerEvents: 'none' };

const TONE_ICON = {
  init: PlayCircle,
  loop: Repeat,
  processing: Sparkles,
  system: Lock,
};

/** Slim phase-band label that separates Init / Loop / Processing sections. */
export const OverviewHeader = ({ data }) => {
  const Icon = TONE_ICON[data.tone] || ArrowDownUp;
  return (
    <div className={`ov-header tone-${data.tone || 'init'}`}>
      <Handle type="target" position={Position.Top} style={HIDDEN_HANDLE} isConnectable={false} />
      <Icon size={15} className="ov-header-icon" />
      <span className="ov-header-label">{data.label}</span>
      {data.sublabel && <span className="ov-header-sub">{data.sublabel}</span>}
      <Handle type="source" position={Position.Bottom} style={HIDDEN_HANDLE} isConnectable={false} />
    </div>
  );
};

/** A single read-only box: an authored behaviour (collapsed) or a locked system step. */
export const OverviewNode = ({ data, selected }) => {
  const setCurrentMainTab = useWorkflowStore((s) => s.setCurrentMainTab);
  const setCurrentStage = useWorkflowStore((s) => s.setCurrentStage);

  const isSystem = !!data.system;
  const canOpen = !isSystem && !!data.navTab && !!data.navTarget;

  const openCanvas = (e) => {
    e.stopPropagation();
    setCurrentMainTab(data.navTab);
    setCurrentStage(data.navTarget);
  };

  return (
    <div
      className={`ov-node ${isSystem ? 'system' : ''} ${selected ? 'selected' : ''}`}
      data-variant={data.variant || 'slate'}
      onClick={canOpen ? openCanvas : undefined}
      title={canOpen ? `Open ${data.navTarget} canvas` : data.source || undefined}
    >
      <Handle type="target" position={Position.Top} style={HIDDEN_HANDLE} isConnectable={false} />

      <div className="ov-node-head">
        {isSystem && <Lock size={12} className="ov-lock" />}
        <span className="ov-node-title">{data.title}</span>
        {data.phaseLabel && (
          <span className={`ov-pill phase-${data.phase || 'none'}`}>
            {data.phaseLabel}
            {data.inferred ? ' ?' : ''}
          </span>
        )}
      </div>

      {(data.forEach || data.iterations || data.intent || data.knob) && (
        <div className="ov-node-meta">
          {data.forEach && <span className="ov-tag loop">↻ {data.forEach}</span>}
          {data.iterations && <span className="ov-tag">×{data.iterations}</span>}
          {data.intent && <span className="ov-tag intent">consumes intent.{data.intent}</span>}
          {data.knob && <span className="ov-tag knob">{data.knob}</span>}
        </div>
      )}

      {data.description && <div className="ov-node-desc">{data.description}</div>}

      {isSystem ? (
        <div className="ov-node-foot system">{data.source}</div>
      ) : (
        canOpen && (
          <button className="ov-open" onClick={openCanvas}>
            <ExternalLink size={11} /> Open canvas
          </button>
        )
      )}

      <Handle type="source" position={Position.Bottom} style={HIDDEN_HANDLE} isConnectable={false} />
    </div>
  );
};
