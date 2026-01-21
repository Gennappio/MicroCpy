import { useState } from 'react';
import { X, Save, Info } from 'lucide-react';
import './ControllerSettings.css';

/**
 * Controller Settings Modal - Configure execution controller for each stage
 */
const ControllerSettings = ({ node, onSave, onClose }) => {
  const [description, setDescription] = useState(node.data.description || '');
  const [enabled, setEnabled] = useState(node.data.enabled !== false);
  const [numberOfSteps, setNumberOfSteps] = useState(node.data.numberOfSteps || 1);

  const handleSave = () => {
    onSave({
      ...node.data,
      description,
      enabled,
      numberOfSteps,
    });
    onClose();
  };

  // Extract stage name from node ID (e.g., "init-initialization" -> "Initialization")
  const stageName = node.id.replace('init-', '');
  const capitalizedStage = stageName.charAt(0).toUpperCase() + stageName.slice(1);

  // Check if this is the macrostep controller
  const isMacrostepController = node.id.includes('macrostep');

  // Check if the steps parameter is connected
  const isStepsParameterConnected = node.data.isStepsParameterConnected || false;

  return (
    <div className="controller-settings-overlay" onClick={onClose}>
      <div className="controller-settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="controller-settings-header">
          <h2>{capitalizedStage} Controller Settings</h2>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="controller-settings-content">
          {/* Info Section */}
          <div className="controller-info-section">
            <div className="info-box">
              <Info size={18} />
              <div className="info-text">
                <strong>Execution Control:</strong> Only nodes connected (directly or indirectly) 
                to this controller will be executed during the {stageName} stage.
              </div>
            </div>
          </div>

          {/* Enable/Disable Toggle */}
          <div className="form-group">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-text">
                {enabled ? 'Stage Enabled' : 'Stage Disabled'}
              </span>
            </label>
            <p className="form-help">
              When disabled, this entire stage will be skipped during execution.
            </p>
          </div>

          {/* Number of steps (only for macrostep controller) */}
          {isMacrostepController && (
            <div className="form-group">
              <label>Number of Steps</label>
              <input
                type="number"
                min={1}
                value={numberOfSteps}
                onChange={(e) => setNumberOfSteps(Math.max(1, parseInt(e.target.value, 10) || 1))}
                className="form-textarea"
                disabled={isStepsParameterConnected}
                style={{ width: '100px' }}
              />
              <p className="form-help">
                {isStepsParameterConnected
                  ? 'This value is controlled by a connected parameter node.'
                  : 'Number of macro-steps to execute in the simulation.'}
              </p>
            </div>
          )}

          {/* Description */}
          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={`Describe the purpose of the ${stageName} stage...`}
              rows={4}
              className="form-textarea"
            />
            <p className="form-help">
              Optional description of what this stage does in your workflow.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="controller-settings-footer">
          <button className="cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button className="save-button" onClick={handleSave}>
            <Save size={16} />
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};

export default ControllerSettings;

