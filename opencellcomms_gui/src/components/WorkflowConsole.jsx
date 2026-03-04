import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Square, Terminal, AlertCircle, CheckCircle, Loader, RefreshCw, Zap } from 'lucide-react';
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
  // Ref to hold the true current buffer - avoids stale closure issues in SSE handler
  const bufferedLogsRef = useRef([]);
  // Ref for resolving per-tab run completion (used in sequential planner runs)
  const completionResolverRef = useRef(null);
  // Ref to track whether a flush is already scheduled (throttle state updates)
  const flushScheduledRef = useRef(false);

  // Use store for persistent logs per workflow (keeping for compatibility)
  const clearLogs = useWorkflowStore((state) => state.clearWorkflowLogs);
  const exportWorkflow = useWorkflowStore((state) => state.exportWorkflow);
  const fetchAllBadgeStats = useWorkflowStore((state) => state.fetchAllBadgeStats);
  const clearObservabilityState = useWorkflowStore((state) => state.clearObservabilityState);
  const getActivePlannerTabs = useWorkflowStore((state) => state.getActivePlannerTabs);

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
      }, 10000);
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

  // Connect to log stream on mount and sync running state
  useEffect(() => {
    connectToLogStream();
    checkStatus();

    return () => {
      disconnectFromLogStream();
    };
  }, []);

  // Add a log to the buffer (not displayed immediately).
  // Uses ref as source of truth to avoid stale closure in SSE handler.
  // Batches React state updates: at most one setBufferedLogs per 150 ms regardless
  // of how many SSE messages arrive, preventing thousands of re-renders per second.
  const addToBuffer = useCallback((type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    bufferedLogsRef.current.push({ type, message, timestamp }); // O(1), no spread
    if (!flushScheduledRef.current) {
      flushScheduledRef.current = true;
      setTimeout(() => {
        setBufferedLogs([...bufferedLogsRef.current]); // one spread per 150 ms max
        flushScheduledRef.current = false;
      }, 150);
    }
  }, []);

  // Refresh: move buffered logs to displayed logs
  const handleRefresh = useCallback(() => {
    const logsToMove = bufferedLogsRef.current;
    if (logsToMove.length === 0) return;
    setDisplayedLogs(prev => [...prev, ...logsToMove]);
    bufferedLogsRef.current = [];
    setBufferedLogs([]);
  }, []);

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/status`);
      const data = await res.json();
      if (data.running) setIsRunning(true);
    } catch (err) {
      // Server may not be available yet
    }
  };

  const handleForceKill = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/force-kill`, { method: 'POST' });
      const data = await response.json();
      if (response.ok) {
        setIsRunning(false);
        const timestamp = new Date().toLocaleTimeString();
        setDisplayedLogs(prev => [...prev, { type: 'warning', message: '⚡ Process forcefully killed', timestamp }]);
      } else {
        const timestamp = new Date().toLocaleTimeString();
        setDisplayedLogs(prev => [...prev, { type: 'error', message: `❌ Force kill failed: ${data.error}`, timestamp }]);
      }
    } catch (err) {
      const timestamp = new Date().toLocaleTimeString();
      setDisplayedLogs(prev => [...prev, { type: 'error', message: `❌ Force kill error: ${err.message}`, timestamp }]);
    }
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
            if (completionResolverRef.current) {
              // Sequential planner run: resolve the per-tab promise
              completionResolverRef.current(data.type);
              completionResolverRef.current = null;
            } else {
              setIsRunning(false);
            }
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

  /**
   * Apply planner tab overrides to an exported workflow JSON.
   * Replaces parameter node data in subworkflows[*].parameters[] with override values.
   */
  const applyOverridesToWorkflow = (workflow, overrides) => {
    const patched = JSON.parse(JSON.stringify(workflow));
    for (const swName of Object.keys(patched.subworkflows)) {
      const sw = patched.subworkflows[swName];
      if (!sw.parameters) continue;
      sw.parameters = sw.parameters.map((param) => {
        const override = overrides[param.id];
        if (!override) return param;
        // Merge override data into the parameter node
        const merged = { ...param };
        if (override.parameters !== undefined) merged.parameters = override.parameters;
        if (override.items !== undefined) merged.items = override.items;
        if (override.entries !== undefined) merged.entries = override.entries;
        if (override.listType !== undefined) merged.listType = override.listType;
        return merged;
      });
    }
    return patched;
  };

  /**
   * Wait for the current run to finish (complete or error) via SSE.
   * Returns a promise that resolves when the SSE handler receives a terminal event.
   */
  const waitForRunCompletion = () => {
    return new Promise((resolve) => {
      completionResolverRef.current = resolve;
    });
  };

  const handleRun = async () => {
    if (isRunning) return;

    setError(null);
    // Clear both displayed and buffered logs
    setDisplayedLogs([]);
    setBufferedLogs([]);
    bufferedLogsRef.current = [];
    clearLogs(workflowName);  // Also clear store for compatibility
    clearObservabilityState();  // Clear previous run's observability data

    try {
      const fullWorkflow = exportWorkflow();
      const activeSubworkflow = fullWorkflow.subworkflows[workflowName];

      if (!activeSubworkflow) {
        throw new Error(`Subworkflow '${workflowName}' not found`);
      }

      const activeTabs = getActivePlannerTabs();
      setIsRunning(true);

      if (activeTabs.length === 0) {
        // No planner tabs: run once with current canvas values (backward compat)
        const timestamp = new Date().toLocaleTimeString();
        setDisplayedLogs([{ type: 'info', message: `🚀 Starting simulation...`, timestamp }]);

        const response = await fetch(`${API_BASE_URL}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            workflow: fullWorkflow,
            entry_subworkflow: 'main',
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to start workflow');
        }

        setDisplayedLogs(prev => [...prev, {
          type: 'info',
          message: `✓ Workflow execution started`,
          timestamp: new Date().toLocaleTimeString(),
        }]);
        // isRunning will be set to false by SSE handler on complete/error

      } else {
        // Sequential planner run: execute each active tab
        const timestamp = new Date().toLocaleTimeString();
        setDisplayedLogs([{
          type: 'info',
          message: `🚀 Starting ${activeTabs.length} planner configuration(s)...`,
          timestamp,
        }]);

        for (let i = 0; i < activeTabs.length; i++) {
          const tab = activeTabs[i];
          const tabWorkflow = applyOverridesToWorkflow(fullWorkflow, tab.parameterOverrides);

          setDisplayedLogs(prev => [...prev, {
            type: 'info',
            message: `▶ [${i + 1}/${activeTabs.length}] Running "${tab.name}"...`,
            timestamp: new Date().toLocaleTimeString(),
          }]);

          const response = await fetch(`${API_BASE_URL}/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              workflow: tabWorkflow,
              entry_subworkflow: 'main',
              run_label: tab.name,
            }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            setDisplayedLogs(prev => [...prev, {
              type: 'error',
              message: `❌ "${tab.name}" failed to start: ${errorData.error || 'Unknown error'}`,
              timestamp: new Date().toLocaleTimeString(),
            }]);
            continue; // Try next tab
          }

          // Wait for this run to complete via SSE
          const result = await waitForRunCompletion();

          setDisplayedLogs(prev => [...prev, {
            type: result === 'complete' ? 'info' : 'error',
            message: result === 'complete'
              ? `✓ "${tab.name}" completed`
              : `✗ "${tab.name}" finished with errors`,
            timestamp: new Date().toLocaleTimeString(),
          }]);
        }

        setDisplayedLogs(prev => [...prev, {
          type: 'info',
          message: `✓ All planner configurations finished`,
          timestamp: new Date().toLocaleTimeString(),
        }]);
        setIsRunning(false);
      }

    } catch (err) {
      setError(err.message);
      setIsRunning(false);
      setDisplayedLogs(prev => [...prev, {
        type: 'error',
        message: `❌ Failed to start: ${err.message}`,
        timestamp: new Date().toLocaleTimeString(),
      }]);
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

          <button
            className="btn-run-console"
            onClick={handleRun}
            disabled={!isConnected || isRunning}
            title={isRunning ? 'Simulation is running' : 'Run workflow'}
          >
            <Play size={14} />
            Run
          </button>

          <button
            className="btn-stop-console"
            onClick={handleStop}
            disabled={!isRunning}
            title={isRunning ? 'Stop workflow' : 'No simulation running'}
          >
            <Square size={14} />
            Stop
          </button>

          <button
            className="btn-force-kill-console"
            onClick={handleForceKill}
            title="Kill any running process (even after page refresh)"
          >
            <Zap size={14} />
            Force Kill
          </button>
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

