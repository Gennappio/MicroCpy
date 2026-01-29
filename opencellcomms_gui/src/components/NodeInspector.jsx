import React, { useState, useEffect } from 'react';
import { X, Pin, PinOff, Info, Settings, Database, FileText, Image, Clock, CheckCircle, AlertCircle, AlertTriangle, Loader } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './NodeInspector.css';

const API_BASE_URL = 'http://localhost:5001';

/**
 * NodeInspector - Right panel for inspecting node execution details
 * 
 * Tabs:
 *   - Overview: Node info, status, timing
 *   - Params: Resolved parameters (TODO: Phase B)
 *   - Context: Before/after snapshots and diff
 *   - Logs: Node-filtered logs
 *   - Artifacts: Produced files (TODO: Phase B)
 */
const NodeInspector = () => {
  const inspector = useWorkflowStore((state) => state.inspector);
  const closeInspector = useWorkflowStore((state) => state.closeInspector);
  const setInspectorTab = useWorkflowStore((state) => state.setInspectorTab);
  const pinInspector = useWorkflowStore((state) => state.pinInspector);
  const currentStage = useWorkflowStore((state) => state.currentStage);
  const selectedNodeByStage = useWorkflowStore((state) => state.selectedNodeByStage);
  const stageNodes = useWorkflowStore((state) => state.stageNodes);
  const workflow = useWorkflowStore((state) => state.workflow);
  const nodeBadgeStatsByScope = useWorkflowStore((state) => state.nodeBadgeStatsByScope);
  
  const [events, setEvents] = useState([]);
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Determine which node to show
  const pinnedNodeId = inspector.pinnedNodeId;
  const selectedNodeId = selectedNodeByStage[currentStage];
  const displayNodeId = pinnedNodeId || selectedNodeId;
  
  // Get node data
  const nodes = stageNodes[currentStage] || [];
  const nodeData = nodes.find(n => n.id === displayNodeId)?.data;
  
  // Get scope key for API calls
  const subworkflowKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] || 'subworkflow';
  const scopeKey = `${subworkflowKind}:${currentStage}`;
  
  // Get badge stats
  const badgeStats = nodeBadgeStatsByScope[scopeKey]?.[displayNodeId];
  
  // Fetch events when tab changes to logs
  useEffect(() => {
    if (inspector.isOpen && inspector.tab === 'logs' && displayNodeId) {
      fetchEvents();
    }
  }, [inspector.isOpen, inspector.tab, displayNodeId, scopeKey]);
  
  // Fetch context when tab changes to context
  useEffect(() => {
    if (inspector.isOpen && inspector.tab === 'context' && displayNodeId) {
      fetchContext();
    }
  }, [inspector.isOpen, inspector.tab, displayNodeId, scopeKey]);
  
  const fetchEvents = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/observability/events?scopeKey=${encodeURIComponent(scopeKey)}&nodeId=${encodeURIComponent(displayNodeId)}&limit=10000`
      );
      const data = await res.json();
      if (data.success) {
        setEvents(data.events || []);
      }
    } catch (err) {
      console.error('Failed to fetch events:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchContext = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/observability/context?scopeKey=${encodeURIComponent(scopeKey)}`
      );
      const data = await res.json();
      if (data.success) {
        setContext(data.snapshot);
      }
    } catch (err) {
      console.error('Failed to fetch context:', err);
    } finally {
      setLoading(false);
    }
  };
  
  if (!inspector.isOpen) {
    return null;
  }
  
  const isPinned = pinnedNodeId === displayNodeId;
  
  const handlePin = () => {
    if (isPinned) {
      pinInspector(null);
    } else {
      pinInspector(displayNodeId);
    }
  };
  
  const statusConfig = {
    idle: { icon: null, color: '#9ca3af', label: 'Idle' },
    running: { icon: Loader, color: '#3b82f6', label: 'Running' },
    ok: { icon: CheckCircle, color: '#10b981', label: 'OK' },
    warn: { icon: AlertTriangle, color: '#f59e0b', label: 'Warning' },
    error: { icon: AlertCircle, color: '#ef4444', label: 'Error' },
    skipped: { icon: null, color: '#6b7280', label: 'Skipped' },
  };
  
  const tabs = [
    { id: 'overview', icon: Info, label: 'Overview' },
    { id: 'context', icon: Database, label: 'Context' },
    { id: 'logs', icon: FileText, label: 'Logs' },
  ];

  return (
    <div className="node-inspector">
      {/* Header */}
      <div className="inspector-header">
        <div className="inspector-title">
          <span className="inspector-node-name">{nodeData?.label || nodeData?.functionName || displayNodeId || 'No node selected'}</span>
          {isPinned && <span className="pinned-indicator">📌</span>}
        </div>
        <div className="inspector-actions">
          {displayNodeId && (
            <button className="inspector-btn" onClick={handlePin} title={isPinned ? 'Unpin' : 'Pin to this node'}>
              {isPinned ? <PinOff size={14} /> : <Pin size={14} />}
            </button>
          )}
          <button className="inspector-btn" onClick={closeInspector} title="Close inspector">
            <X size={14} />
          </button>
        </div>
      </div>
      
      {/* Tab bar */}
      <div className="inspector-tabs">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`inspector-tab ${inspector.tab === tab.id ? 'active' : ''}`}
              onClick={() => setInspectorTab(tab.id)}
            >
              <Icon size={12} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      
      {/* Content */}
      <div className="inspector-content">
        {!displayNodeId ? (
          <div className="inspector-empty">
            <Info size={32} opacity={0.3} />
            <p>Select a node to inspect</p>
          </div>
        ) : (
          <>
            {inspector.tab === 'overview' && <OverviewTab nodeData={nodeData} badgeStats={badgeStats} statusConfig={statusConfig} />}
            {inspector.tab === 'context' && <ContextTab context={context} loading={loading} />}
            {inspector.tab === 'logs' && <LogsTab events={events} loading={loading} />}
          </>
        )}
      </div>
    </div>
  );
};

// ===== Tab Components =====

const OverviewTab = ({ nodeData, badgeStats, statusConfig }) => {
  const status = badgeStats?.status || 'idle';
  const config = statusConfig[status] || statusConfig.idle;
  const StatusIcon = config.icon;

  return (
    <div className="tab-overview">
      <div className="overview-section">
        <h4>Node Information</h4>
        <div className="overview-row">
          <span className="label">Name:</span>
          <span className="value">{nodeData?.label || nodeData?.customName || 'Unnamed'}</span>
        </div>
        <div className="overview-row">
          <span className="label">Function:</span>
          <span className="value mono">{nodeData?.functionName || 'N/A'}</span>
        </div>
        {nodeData?.functionFile && (
          <div className="overview-row">
            <span className="label">File:</span>
            <span className="value mono">{nodeData.functionFile}</span>
          </div>
        )}
        <div className="overview-row">
          <span className="label">Enabled:</span>
          <span className="value">{nodeData?.enabled !== false ? 'Yes' : 'No'}</span>
        </div>
      </div>

      {badgeStats && (
        <div className="overview-section">
          <h4>Last Execution</h4>
          <div className="overview-row">
            <span className="label">Status:</span>
            <span className="value" style={{ color: config.color, display: 'flex', alignItems: 'center', gap: '4px' }}>
              {StatusIcon && <StatusIcon size={14} />}
              {config.label}
            </span>
          </div>
          {badgeStats.lastDurationMs && (
            <div className="overview-row">
              <span className="label">Duration:</span>
              <span className="value"><Clock size={12} style={{ marginRight: 4 }} />{badgeStats.lastDurationMs.toFixed(1)}ms</span>
            </div>
          )}
          {badgeStats.lastStart && (
            <div className="overview-row">
              <span className="label">Started:</span>
              <span className="value">{new Date(badgeStats.lastStart).toLocaleTimeString()}</span>
            </div>
          )}
          <div className="overview-row">
            <span className="label">Log counts:</span>
            <span className="value log-counts">
              <span className="log-info">{badgeStats.logCounts?.info || 0} info</span>
              <span className="log-warn">{badgeStats.logCounts?.warn || 0} warn</span>
              <span className="log-error">{badgeStats.logCounts?.error || 0} error</span>
            </span>
          </div>
          {badgeStats.writes > 0 && (
            <div className="overview-row">
              <span className="label">Context writes:</span>
              <span className="value">{badgeStats.writes} key(s)</span>
            </div>
          )}
        </div>
      )}

      {!badgeStats && (
        <div className="overview-section">
          <p className="no-data">No execution data available. Run the workflow to see execution details.</p>
        </div>
      )}
    </div>
  );
};

const ContextTab = ({ context, loading }) => {
  const [viewMode, setViewMode] = React.useState('current');  // 'current' | 'diff'
  const [diff, setDiff] = React.useState(null);
  const [diffLoading, setDiffLoading] = React.useState(false);

  const fetchDiff = async () => {
    if (!context || context.version <= 1) return;
    setDiffLoading(true);
    try {
      const scopeKey = context.scopeKey;
      const res = await fetch(
        `${API_BASE_URL}/api/observability/diff?scopeKey=${encodeURIComponent(scopeKey)}&from=${context.version - 1}&to=${context.version}`
      );
      const data = await res.json();
      if (data.success) {
        setDiff(data.diff);
      }
    } catch (err) {
      console.error('Failed to fetch diff:', err);
    } finally {
      setDiffLoading(false);
    }
  };

  React.useEffect(() => {
    if (viewMode === 'diff' && context && !diff) {
      fetchDiff();
    }
  }, [viewMode, context]);

  if (loading) {
    return <div className="tab-loading"><Loader size={24} className="spinning" /><p>Loading context...</p></div>;
  }

  if (!context) {
    return <div className="tab-empty"><Database size={32} opacity={0.3} /><p>No context snapshot available</p></div>;
  }

  const keys = Object.keys(context.keys || {});

  return (
    <div className="tab-context">
      {/* View mode toggle */}
      <div className="context-toolbar">
        <button
          className={`view-mode-btn ${viewMode === 'current' ? 'active' : ''}`}
          onClick={() => setViewMode('current')}
        >
          Current
        </button>
        <button
          className={`view-mode-btn ${viewMode === 'diff' ? 'active' : ''}`}
          onClick={() => setViewMode('diff')}
          disabled={context.version <= 1}
        >
          Changes
        </button>
        <span className="context-version">v{context.version}</span>
      </div>

      {viewMode === 'current' && (
        <>
          <div className="context-info">
            <span>{keys.length} key(s)</span>
          </div>
          <div className="context-keys">
            {keys.map(key => {
              const val = context.keys[key];
              return (
                <div key={key} className="context-key">
                  <span className="key-name">{key}</span>
                  <span className="key-type">{val.type}</span>
                  <span className="key-preview">{typeof val.preview === 'string' ? val.preview.substring(0, 50) : JSON.stringify(val.preview)?.substring(0, 50)}</span>
                </div>
              );
            })}
          </div>
        </>
      )}

      {viewMode === 'diff' && (
        <>
          {diffLoading ? (
            <div className="tab-loading"><Loader size={20} className="spinning" /><p>Loading diff...</p></div>
          ) : diff ? (
            <div className="context-diff">
              {/* Added keys */}
              {Object.keys(diff.added || {}).length > 0 && (
                <div className="diff-section diff-added">
                  <h5>+ Added ({Object.keys(diff.added).length})</h5>
                  {Object.entries(diff.added).map(([key, val]) => (
                    <div key={key} className="diff-key added">
                      <span className="key-name">{key}</span>
                      <span className="key-type">{val.type}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Changed keys */}
              {Object.keys(diff.changed || {}).length > 0 && (
                <div className="diff-section diff-changed">
                  <h5>~ Changed ({Object.keys(diff.changed).length})</h5>
                  {Object.entries(diff.changed).map(([key, { before, after }]) => (
                    <div key={key} className="diff-key changed">
                      <span className="key-name">{key}</span>
                      <span className="key-type">{after.type}</span>
                      <div className="diff-values">
                        <div className="diff-before">
                          <span className="diff-label">Before:</span>
                          <span className="diff-value">{typeof before.preview === 'string' ? before.preview : JSON.stringify(before.preview, null, 2)}</span>
                        </div>
                        <div className="diff-after">
                          <span className="diff-label">After:</span>
                          <span className="diff-value">{typeof after.preview === 'string' ? after.preview : JSON.stringify(after.preview, null, 2)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Removed keys */}
              {Object.keys(diff.removed || {}).length > 0 && (
                <div className="diff-section diff-removed">
                  <h5>- Removed ({Object.keys(diff.removed).length})</h5>
                  {Object.entries(diff.removed).map(([key, val]) => (
                    <div key={key} className="diff-key removed">
                      <span className="key-name">{key}</span>
                      <span className="key-type">{val.type}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* No changes */}
              {Object.keys(diff.added || {}).length === 0 &&
               Object.keys(diff.changed || {}).length === 0 &&
               Object.keys(diff.removed || {}).length === 0 && (
                <div className="no-changes">No changes in this version</div>
              )}
            </div>
          ) : (
            <div className="tab-empty"><p>No diff available</p></div>
          )}
        </>
      )}
    </div>
  );
};

const LogsTab = ({ events, loading }) => {
  if (loading) {
    return <div className="tab-loading"><Loader size={24} className="spinning" /><p>Loading logs...</p></div>;
  }

  const logEvents = events.filter(e => e.event === 'log' || e.event === 'node_start' || e.event === 'node_end');

  if (logEvents.length === 0) {
    return <div className="tab-empty"><FileText size={32} opacity={0.3} /><p>No log events for this node</p></div>;
  }

  return (
    <div className="tab-logs">
      {logEvents.map((event, idx) => (
        <div key={idx} className={`log-entry log-${event.level?.toLowerCase() || 'info'}`}>
          <span className="log-time">{new Date(event.ts).toLocaleTimeString()}</span>
          <span className="log-event">{event.event}</span>
          <span className="log-message">
            {event.payload?.message || event.payload?.status || JSON.stringify(event.payload)}
          </span>
        </div>
      ))}
    </div>
  );
};

export default NodeInspector;

