import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Terminal, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './SimulationRunner.css';

const API_BASE_URL = 'http://localhost:5001/api';

/**
 * SimulationRunner Component
 * Provides UI for running MicroC simulations and viewing real-time logs
 */
const SimulationRunner = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);
  const exportWorkflow = useWorkflowStore((state) => state.exportWorkflow);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Connect to log stream on mount
  useEffect(() => {
    connectToLogStream();
    checkServerHealth();
    
    return () => {
      disconnectFromLogStream();
    };
  }, []);

  const checkServerHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      
      if (data.status === 'healthy') {
        addLog('info', `✓ Backend server connected`);
        if (!data.microc_exists) {
          addLog('error', `✗ MicroC not found at: ${data.microc_path}`);
        }
      }
    } catch (err) {
      addLog('error', '✗ Backend server not reachable. Make sure to start the server with: python server/api.py');
      setError('Backend server not running');
    }
  };

  const connectToLogStream = () => {
    try {
      const eventSource = new EventSource(`${API_BASE_URL}/logs`);
      
      eventSource.onopen = () => {
        setIsConnected(true);
        console.log('[SSE] Connected to log stream');
      };
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'heartbeat') {
            // Ignore heartbeat messages
            return;
          }
          
          if (data.type === 'connected') {
            setIsConnected(true);
            return;
          }
          
          if (data.message) {
            addLog(data.type, data.message);
          }
          
          // Check for completion
          if (data.type === 'complete' || data.type === 'error') {
            setIsRunning(false);
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

  const addLog = (type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { type, message, timestamp }]);
  };

  const handleRun = async () => {
    if (isRunning) return;

    setError(null);
    setLogs([]);

    try {
      // Export current workflow
      const workflow = exportWorkflow();

      addLog('info', '📋 Exporting workflow...');

      // Prepare request body
      const requestBody = {
        workflow: workflow,
      };

      // Always run in workflow-only mode from the GUI
      addLog('info', '🚀 Starting workflow execution');

      // Start simulation
      const response = await fetch(`${API_BASE_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start simulation');
      }

      const data = await response.json();
      setIsRunning(true);
      addLog('info', `✓ Workflow execution started`);

    } catch (err) {
      setError(err.message);
      addLog('error', `❌ Failed to start: ${err.message}`);
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
        throw new Error(errorData.error || 'Failed to stop simulation');
      }
      
      setIsRunning(false);
      addLog('warning', '⏹️ Simulation stopped by user');
      
    } catch (err) {
      setError(err.message);
      addLog('error', `❌ Failed to stop: ${err.message}`);
    }
  };

  const getLogIcon = (type) => {
    switch (type) {
      case 'error':
        return <AlertCircle size={14} className="log-icon error" />;
      case 'complete':
        return <CheckCircle size={14} className="log-icon success" />;
      case 'warning':
        return <AlertCircle size={14} className="log-icon warning" />;
      default:
        return <Terminal size={14} className="log-icon info" />;
    }
  };

  return (
    <div className="simulation-runner">
      <div className="runner-header">
        <div className="header-left">
          <Terminal size={20} />
          <h3>Simulation Runner</h3>
          {isConnected && <span className="connection-status connected">●</span>}
          {!isConnected && <span className="connection-status disconnected">●</span>}
        </div>

        <div className="header-controls">
          {!isRunning ? (
            <button
              className="btn btn-run"
              onClick={handleRun}
              disabled={!isConnected}
            >
              <Play size={16} />
              Run Workflow
            </button>
          ) : (
            <button className="btn btn-stop" onClick={handleStop}>
              <Square size={16} />
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Config file input removed: GUI runs workflows only */}

      {error && (
        <div className="error-banner">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="logs-container">
        {logs.length === 0 ? (
          <div className="logs-empty">
            <Terminal size={48} />
            <p>No logs yet. Click "Run Simulation" to start.</p>
          </div>
        ) : (
          <div className="logs-content">
            {logs.map((log, index) => (
              <div key={index} className={`log-entry log-${log.type}`}>
                <span className="log-timestamp">{log.timestamp}</span>
                {getLogIcon(log.type)}
                <span className="log-message">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {isRunning && (
        <div className="running-indicator">
          <Loader size={16} className="spinner" />
          <span>Simulation running...</span>
        </div>
      )}
    </div>
  );
};

export default SimulationRunner;

