import { Handle, Position } from 'reactflow';
import { Zap } from 'lucide-react';
import './InitNode.css';

/**
 * Init Node - The starting point for execution flow
 * Only nodes connected (directly or indirectly) to Init will be executed
 * This node cannot be deleted and is always present in every stage
 */
const InitNode = ({ id, data, selected }) => {
  return (
    <div className={`init-node ${selected ? 'selected' : ''}`}>
      <div className="init-node-content">
        <Zap size={24} className="init-icon" />
        <span className="init-label">INIT</span>
      </div>
      
      {/* Output handle - connects to first function in execution chain */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="init-out"
        className="init-handle-output"
        style={{
          background: '#dc2626',
          width: '12px',
          height: '12px',
          border: '3px solid white',
        }}
      />
    </div>
  );
};

export default InitNode;

