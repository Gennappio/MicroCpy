import React from 'react';
import { Clock, AlertCircle, AlertTriangle, Info, CheckCircle, Loader } from 'lucide-react';
import './NodeBadge.css';

/**
 * NodeBadge - Displays execution status and log counts for workflow nodes
 * 
 * Props:
 *   stats: BadgeStats object { status, lastDurationMs, logCounts: {info, warn, error}, writes }
 *   onClick: (badgeType) => void - called when a badge is clicked
 *   compact: boolean - whether to show compact view
 */
const NodeBadge = ({ stats, onClick, compact = false }) => {
  if (!stats) {
    return null;
  }

  const { status, lastDurationMs, logCounts, writes } = stats;

  // Status icon and color mapping
  const statusConfig = {
    idle: { icon: null, color: '#9ca3af', label: 'Idle' },
    running: { icon: Loader, color: '#3b82f6', label: 'Running' },
    ok: { icon: CheckCircle, color: '#10b981', label: 'OK' },
    warn: { icon: AlertTriangle, color: '#f59e0b', label: 'Warning' },
    error: { icon: AlertCircle, color: '#ef4444', label: 'Error' },
    skipped: { icon: null, color: '#6b7280', label: 'Skipped' },
  };

  const config = statusConfig[status] || statusConfig.idle;
  const StatusIcon = config.icon;

  // Format duration
  const formatDuration = (ms) => {
    if (!ms) return null;
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const duration = formatDuration(lastDurationMs);

  // Determine which log badge to show (priority: error > warn > info)
  const hasErrors = logCounts?.error > 0;
  const hasWarnings = logCounts?.warn > 0;
  const hasInfo = logCounts?.info > 0;

  const handleClick = (e, badgeType) => {
    e.stopPropagation();
    if (onClick) {
      onClick(badgeType);
    }
  };

  if (compact) {
    // Compact mode: just status dot
    return (
      <div className="node-badge compact" onClick={(e) => handleClick(e, 'status')}>
        <div className="status-dot" style={{ backgroundColor: config.color }} title={config.label} />
      </div>
    );
  }

  return (
    <div className="node-badge">
      {/* Status indicator */}
      {StatusIcon && (
        <button
          className="badge-item status"
          style={{ color: config.color }}
          onClick={(e) => handleClick(e, 'status')}
          title={config.label}
        >
          <StatusIcon size={12} className={status === 'running' ? 'spinning' : ''} />
        </button>
      )}

      {/* Duration badge */}
      {duration && (
        <button
          className="badge-item timing"
          onClick={(e) => handleClick(e, 'timing')}
          title={`Last execution: ${duration}`}
        >
          <Clock size={10} />
          <span>{duration}</span>
        </button>
      )}

      {/* Error count badge */}
      {hasErrors && (
        <button
          className="badge-item error"
          onClick={(e) => handleClick(e, 'logs')}
          title={`${logCounts.error} error(s)`}
        >
          <AlertCircle size={10} />
          <span>{logCounts.error}</span>
        </button>
      )}

      {/* Warning count badge (only if no errors) */}
      {!hasErrors && hasWarnings && (
        <button
          className="badge-item warn"
          onClick={(e) => handleClick(e, 'logs')}
          title={`${logCounts.warn} warning(s)`}
        >
          <AlertTriangle size={10} />
          <span>{logCounts.warn}</span>
        </button>
      )}

      {/* Info count badge (only if no errors or warnings, and has info) */}
      {!hasErrors && !hasWarnings && hasInfo && (
        <button
          className="badge-item info"
          onClick={(e) => handleClick(e, 'logs')}
          title={`${logCounts.info} log message(s)`}
        >
          <Info size={10} />
          <span>{logCounts.info}</span>
        </button>
      )}

      {/* Context writes indicator */}
      {writes > 0 && (
        <button
          className="badge-item writes"
          onClick={(e) => handleClick(e, 'context')}
          title={`${writes} context key(s) written`}
        >
          <span className="writes-count">+{writes}</span>
        </button>
      )}
    </div>
  );
};

export default NodeBadge;

