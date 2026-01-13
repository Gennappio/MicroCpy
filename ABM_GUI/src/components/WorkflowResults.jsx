import { useState, useEffect } from 'react';
import { Image, RefreshCw, ChevronDown } from 'lucide-react';
import './WorkflowResults.css';

const API_BASE_URL = 'http://localhost:5001';

/**
 * WorkflowResults - Per-workflow results viewer with integrated dropdown
 */
function WorkflowResults({ workflowName }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPlot, setSelectedPlot] = useState(null);
  const [availablePlots, setAvailablePlots] = useState([]);

  useEffect(() => {
    loadResults();
  }, [workflowName]);

  const loadResults = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/results/list`);
      const data = await res.json();
      
      if (data.success) {
        setResults(data.results);
        
        // Filter plots for this workflow
        const workflowResults = data.results.filter(r => 
          r.name.includes(workflowName) || r.name === workflowName
        );
        
        // Collect all plots from workflow results
        const plots = [];
        workflowResults.forEach(result => {
          result.plots.forEach(plot => {
            plots.push({
              ...plot,
              resultName: result.name,
              timestamp: result.timestamp
            });
          });
        });
        
        setAvailablePlots(plots);
        
        // Auto-select the first plot
        if (plots.length > 0) {
          setSelectedPlot(plots[0]);
        }
      } else {
        setError(data.error || 'Failed to load results');
      }
    } catch (err) {
      console.error('Error loading results:', err);
      setError(`Failed to load results: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePlotSelect = (e) => {
    const plotPath = e.target.value;
    const plot = availablePlots.find(p => p.path === plotPath);
    setSelectedPlot(plot);
  };

  return (
    <div className="workflow-results">
      {/* Results Header with Dropdown */}
      <div className="results-header">
        <div className="results-title">
          <Image size={16} />
          <span>Results</span>
        </div>
        
        <div className="results-controls">
          <button 
            className="btn-refresh" 
            onClick={loadResults} 
            disabled={loading}
            title="Refresh results"
          >
            <RefreshCw size={12} className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      {/* Dropdown Menu */}
      <div className="results-dropdown">
        <select 
          className="plot-selector"
          value={selectedPlot?.path || ''}
          onChange={handlePlotSelect}
          disabled={availablePlots.length === 0}
        >
          {availablePlots.length === 0 ? (
            <option value="">No results available</option>
          ) : (
            <>
              <option value="">Select a plot...</option>
              {availablePlots.map(plot => (
                <option key={plot.path} value={plot.path}>
                  {plot.category} - {plot.name}
                </option>
              ))}
            </>
          )}
        </select>
        <ChevronDown size={14} className="dropdown-icon" />
      </div>

      {/* Plot Viewer */}
      <div className="results-viewer">
        {error && (
          <div className="results-error">
            <p>{error}</p>
          </div>
        )}
        
        {loading ? (
          <div className="results-empty">
            <RefreshCw size={32} className="spinning" opacity={0.3} />
            <p>Loading results...</p>
          </div>
        ) : selectedPlot ? (
          <div className="plot-display">
            <img 
              src={`${API_BASE_URL}/api/results/plot/${selectedPlot.path}`}
              alt={selectedPlot.name}
              className="plot-image"
            />
          </div>
        ) : (
          <div className="results-empty">
            <Image size={32} opacity={0.3} />
            <p>No plot selected</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowResults;

