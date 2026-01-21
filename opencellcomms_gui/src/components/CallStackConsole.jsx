import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Layers, AlertCircle } from 'lucide-react';
import './CallStackConsole.css';

/**
 * Call Stack Console - Shows the current execution call stack
 * Displays nested sub-workflow calls with iteration information
 */
const CallStackConsole = ({ callStack = [], isRunning = false }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  // Auto-expand when running
  useEffect(() => {
    if (isRunning && callStack.length > 0) {
      setIsExpanded(true);
    }
  }, [isRunning, callStack]);

  return (
    <div className={`call-stack-console ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="console-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="header-left">
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <Layers size={16} />
          <span className="header-title">Call Stack</span>
          {callStack.length > 0 && (
            <span className="stack-depth-badge">{callStack.length}</span>
          )}
        </div>
        {isRunning && (
          <div className="running-indicator">
            <div className="pulse-dot" />
            <span>Running</span>
          </div>
        )}
      </div>

      {isExpanded && (
        <div className="console-content">
          {callStack.length === 0 ? (
            <div className="empty-stack">
              <AlertCircle size={20} />
              <span>No active execution</span>
            </div>
          ) : (
            <div className="stack-list">
              {callStack.map((entry, index) => {
                const isLast = index === callStack.length - 1;
                const depth = index;
                
                return (
                  <div
                    key={index}
                    className={`stack-entry ${isLast ? 'active' : ''}`}
                    style={{ paddingLeft: `${depth * 16 + 12}px` }}
                  >
                    <div className="entry-connector">
                      {depth > 0 && <div className="connector-line" />}
                      <div className="entry-dot" />
                    </div>
                    <div className="entry-content">
                      <div className="entry-name">{entry.name}</div>
                      {entry.total_iterations > 1 && (
                        <div className="entry-iteration">
                          Iteration {entry.iteration} / {entry.total_iterations}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CallStackConsole;

