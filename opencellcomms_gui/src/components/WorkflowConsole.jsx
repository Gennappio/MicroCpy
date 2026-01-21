import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Terminal, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './WorkflowConsole.css';

const API_BASE_URL = 'http://localhost:5001/api';

/**
 * WorkflowConsole - Per-workflow console with integrated Run/Stop button
 */
const WorkflowConsole = ({ workflowName }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);
  const badgePollingRef = useRef(null);

  // Use store for persistent logs per workflow
  const logs = useWorkflowStore((state) => state.workflowLogs[workflowName] || []);
  const addLog = useWorkflowStore((state) => state.addWorkflowLog);
  const clearLogs = useWorkflowStore((state) => state.clearWorkflowLogs);
  const exportWorkflow = useWorkflowStore((state) => state.exportWorkflow);
  const fetchAllBadgeStats = useWorkflowStore((state) => state.fetchAllBadgeStats);
  const clearObservabilityState = useWorkflowStore((state) => state.clearObservabilityState);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

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
            addLog(workflowName, data.type, data.message);
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
    clearLogs(workflowName);
    clearObservabilityState();  // Clear previous run's observability data

    try {
      const fullWorkflow = exportWorkflow();

      // Section 9.2: Send full workflow with entry_subworkflow parameter
      // No need to rename or modify the workflow structure
      const activeSubworkflow = fullWorkflow.subworkflows[workflowName];

      if (!activeSubworkflow) {
        throw new Error(`Subworkflow '${workflowName}' not found`);
      }

      addLog(workflowName, 'info', `🚀 Running workflow from entry point: ${workflowName}`);

      const response = await fetch(`${API_BASE_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow: fullWorkflow,  // Send full workflow unchanged
          entry_subworkflow: workflowName  // Specify entry point (Section 9.2)
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start workflow');
      }

      setIsRunning(true);
      addLog(workflowName, 'info', `✓ Workflow execution started`);

    } catch (err) {
      setError(err.message);
      addLog(workflowName, 'error', `❌ Failed to start: ${err.message}`);
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
      addLog(workflowName, 'warning', '⏹️ Workflow stopped by user');
      
    } catch (err) {
      setError(err.message);
      addLog(workflowName, 'error', `❌ Failed to stop: ${err.message}`);
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
      {/* Console Header with Run/Stop Button */}
      <div className="console-header">
        <div className="console-title">
          <Terminal size={16} />
          <span>Console</span>
          {isConnected && <span className="status-dot connected" />}
          {!isConnected && <span className="status-dot disconnected" />}
        </div>

        <div className="console-controls">
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

      {/* Logs Display */}
      <div className="console-logs">
        {logs.length === 0 ? (
          <div className="console-empty">
            <Terminal size={32} opacity={0.3} />
            <p>No logs yet</p>
          </div>
        ) : (
          <div className="console-content">
            {logs.map((log, index) => (
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

      {/* Running Indicator */}
      {isRunning && (
        <div className="console-running">
          <Loader size={12} className="spinner" />
          <span>Running...</span>
        </div>
      )}
    </div>
  );
};

export default WorkflowConsole;

