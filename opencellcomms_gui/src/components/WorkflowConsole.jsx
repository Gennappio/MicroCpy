import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Terminal, AlertCircle, CheckCircle, Loader, RefreshCw } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './WorkflowConsole.css';

const API_BASE_URL = 'http://localhost:5001/api';

/**
 * WorkflowConsole - Per-workflow console with integrated Run/Stop button
 * Logs are buffered and only displayed on refresh to reduce UI clutter during simulation runs.
 */
const WorkflowConsole = ({ workflowName }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  // Buffered logs: logs received from SSE but not yet displayed
  const [bufferedLogs, setBufferedLogs] = useState([]);
  // Displayed logs: logs currently shown in the UI
  const [displayedLogs, setDisplayedLogs] = useState([]);

  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);
  const badgePollingRef = useRef(null);

  // Use store for persistent logs per workflow (keeping for compatibility)
  const clearLogs = useWorkflowStore((state) => state.clearWorkflowLogs);
  const exportWorkflow = useWorkflowStore((state) => state.exportWorkflow);
  const fetchAllBadgeStats = useWorkflowStore((state) => state.fetchAllBadgeStats);
  const clearObservabilityState = useWorkflowStore((state) => state.clearObservabilityState);

  // Auto-scroll to bottom when displayed logs change (after refresh)
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayedLogs]);

  // Poll for badge stats while running
  useEffect(() => {
    if (isRunning) {
      // Start polling every 2 seconds
      const pollInterval = setInterval(() => {
        fetchAllBadgeStats();
      }, 2000);
      badgePollingRef.current = pollInterval;

      return () => {
        if (badgePollingRef.current) {
          clearInterval(badgePollingRef.current);
          badgePollingRef.current = null;
        }
      };
    } else {
      // Stop polling when not running
      if (badgePollingRef.current) {
        clearInterval(badgePollingRef.current);
        badgePollingRef.current = null;
      }
    }
  }, [isRunning, fetchAllBadgeStats]);

  // Connect to log stream on mount
  useEffect(() => {
    connectToLogStream();

    return () => {
      disconnectFromLogStream();
    };
  }, []);

  // Add a log to the buffer (not displayed immediately)
  const addToBuffer = (type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setBufferedLogs(prev => [...prev, { type, message, timestamp }]);
  };

  // Refresh: move buffered logs to displayed logs
  const handleRefresh = () => {
    setDisplayedLogs(prev => [...prev, ...bufferedLogs]);
    setBufferedLogs([]);
  };

  const connectToLogStream = () => {
    try {
      const eventSource = new EventSource(`${API_BASE_URL}/logs`);

      eventSource.onopen = () => {
        setIsConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'heartbeat' || data.type === 'connected') {
            return;
          }

          if (data.message) {
            // Buffer the log instead of displaying immediately
            addToBuffer(data.type, data.message);
          }

          // Check for completion - fetch final badge stats
          if (data.type === 'complete' || data.type === 'error') {
            setIsRunning(false);
            // Fetch final badge stats after a small delay to ensure files are written
            setTimeout(() => {
              fetchAllBadgeStats();
            }, 500);
          }
        } catch (err) {
          console.error('[SSE] Failed to parse message:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('[SSE] Connection error:', err);
        setIsConnected(false);
        eventSource.close();

        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (!eventSourceRef.current) {
            connectToLogStream();
          }
        }, 5000);
      };

      eventSourceRef.current = eventSource;
    } catch (err) {
      console.error('[SSE] Failed to connect:', err);
      setIsConnected(false);
    }
  };

  const disconnectFromLogStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  };

  const handleRun = async () => {
    if (isRunning) return;

    setError(null);
    // Clear both displayed and buffered logs
    setDisplayedLogs([]);
    setBufferedLogs([]);
    clearLogs(workflowName);  // Also clear store for compatibility
    clearObservabilityState();  // Clear previous run's observability data

    try {
      const fullWorkflow = exportWorkflow();

      // Section 9.2: Send full workflow with entry_subworkflow parameter
      // No need to rename or modify the workflow structure
      const activeSubworkflow = fullWorkflow.subworkflows[workflowName];

      if (!activeSubworkflow) {
        throw new Error(`Subworkflow '${workflowName}' not found`);
      }

      // Add to displayed logs immediately (not buffered) for user feedback
      const timestamp = new Date().toLocaleTimeString();
      setDisplayedLogs([{ type: 'info', message: `🚀 Starting simulation...`, timestamp }]);

      const response = await fetch(`${API_BASE_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow: fullWorkflow,  // Send full workflow unchanged
          entry_subworkflow: 'main'  // Always run from main entry point
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start workflow');
      }

      setIsRunning(true);
      setDisplayedLogs(prev => [...prev, { type: 'info', message: `✓ Workflow execution started`, timestamp: new Date().toLocaleTimeString() }]);

    } catch (err) {
      setError(err.message);
      setDisplayedLogs(prev => [...prev, { type: 'error', message: `❌ Failed to start: ${err.message}`, timestamp: new Date().toLocaleTimeString() }]);
    }
  };

  const handleStop = async () => {
    if (!isRunning) return;

    try {
      const response = await fetch(`${API_BASE_URL}/stop`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to stop workflow');
      }

      setIsRunning(false);
      // Add stop message to displayed logs immediately
      setDisplayedLogs(prev => [...prev, { type: 'warning', message: '⏹️ Workflow stopped by user', timestamp: new Date().toLocaleTimeString() }]);

    } catch (err) {
      setError(err.message);
      setDisplayedLogs(prev => [...prev, { type: 'error', message: `❌ Failed to stop: ${err.message}`, timestamp: new Date().toLocaleTimeString() }]);
    }
  };

  const getLogIcon = (type) => {
    switch (type) {
      case 'error':
        return <AlertCircle size={12} className="log-icon error" />;
      case 'complete':
        return <CheckCircle size={12} className="log-icon success" />;
      case 'warning':
        return <AlertCircle size={12} className="log-icon warning" />;
      default:
        return <Terminal size={12} className="log-icon info" />;
    }
  };

  return (
    <div className="workflow-console">
      {/* Console Header with Run/Stop/Refresh Buttons */}
      <div className="console-header">
        <div className="console-title">
          <Terminal size={16} />
          <span>Console</span>
          {isConnected && <span className="status-dot connected" />}
          {!isConnected && <span className="status-dot disconnected" />}
        </div>

        <div className="console-controls">
          {/* Refresh Button with pending count badge */}
          <button
            className="btn-refresh-console"
            onClick={handleRefresh}
            disabled={bufferedLogs.length === 0}
            title={bufferedLogs.length > 0 ? `Refresh (${bufferedLogs.length} new logs)` : 'No new logs'}
          >
            <RefreshCw size={14} />
            Refresh
            {bufferedLogs.length > 0 && (
              <span className="pending-badge">{bufferedLogs.length}</span>
            )}
          </button>

          {!isRunning ? (
            <button
              className="btn-run-console"
              onClick={handleRun}
              disabled={!isConnected}
              title="Run workflow"
            >
              <Play size={14} />
              Run
            </button>
          ) : (
            <button className="btn-stop-console" onClick={handleStop} title="Stop workflow">
              <Square size={14} />
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Logs Display - shows only displayedLogs, not real-time */}
      <div className="console-logs">
        {displayedLogs.length === 0 ? (
          <div className="console-empty">
            <Terminal size={32} opacity={0.3} />
            <p>No logs yet</p>
            {bufferedLogs.length > 0 && (
              <p className="buffer-hint">{bufferedLogs.length} logs pending - click Refresh to view</p>
            )}
          </div>
        ) : (
          <div className="console-content">
            {displayedLogs.map((log, index) => (
              <div key={index} className={`console-log log-${log.type}`}>
                <span className="log-time">{log.timestamp}</span>
                {getLogIcon(log.type)}
                <span className="log-text">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* Running Indicator with pending logs count */}
      {isRunning && (
        <div className="console-running">
          <Loader size={12} className="spinner" />
          <span>Running... {bufferedLogs.length > 0 && `(${bufferedLogs.length} logs pending)`}</span>
        </div>
      )}
    </div>
  );
};

export default WorkflowConsole;

