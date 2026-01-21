import { useState, useEffect } from 'react';
import { FolderOpen, Image, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import './ResultsExplorer.css';

const API_BASE_URL = 'http://localhost:5001';

function ResultsExplorer() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedResults, setExpandedResults] = useState(new Set());
  const [selectedPlot, setSelectedPlot] = useState(null);

  useEffect(() => {
    loadResults();
  }, []);

  const loadResults = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/results/list`);
      const data = await res.json();
      
      if (data.success) {
        setResults(data.results);
        // Auto-expand the first result
        if (data.results.length > 0) {
          setExpandedResults(new Set([data.results[0].name]));
          // Auto-select the first plot
          if (data.results[0].plots.length > 0) {
            setSelectedPlot(data.results[0].plots[0]);
          }
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

  const toggleExpanded = (resultName) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(resultName)) {
      newExpanded.delete(resultName);
    } else {
      newExpanded.add(resultName);
    }
    setExpandedResults(newExpanded);
  };

  const groupPlotsByCategory = (plots) => {
    const grouped = {};
    plots.forEach(plot => {
      if (!grouped[plot.category]) {
        grouped[plot.category] = [];
      }
      grouped[plot.category].push(plot);
    });
    return grouped;
  };

  const getCategoryIcon = (category) => {
    return <Image size={14} />;
  };

  const formatTimestamp = (timestamp) => {
    // Format: 20251116_130654 -> Nov 16, 2025 13:06:54
    if (timestamp.match(/^\d{8}_\d{6}$/)) {
      const year = timestamp.substring(0, 4);
      const month = timestamp.substring(4, 6);
      const day = timestamp.substring(6, 8);
      const hour = timestamp.substring(9, 11);
      const minute = timestamp.substring(11, 13);
      const second = timestamp.substring(13, 15);
      
      const date = new Date(year, month - 1, day, hour, minute, second);
      return date.toLocaleString();
    }
    return timestamp;
  };

  return (
    <div className="results-explorer">
      <div className="results-sidebar">
        <div className="results-header">
          <h2>
            <FolderOpen size={20} />
            Simulation Results
          </h2>
          <button className="btn btn-sm btn-secondary" onClick={loadResults} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spinning' : ''} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading-message">Loading results...</div>
        ) : results.length === 0 ? (
          <div className="empty-message">
            <FolderOpen size={48} />
            <p>No simulation results found</p>
            <p className="hint">Run a simulation to see results here</p>
          </div>
        ) : (
          <div className="results-list">
            {results.map(result => {
              const isExpanded = expandedResults.has(result.name);
              const groupedPlots = groupPlotsByCategory(result.plots);
              
              return (
                <div key={result.name} className="result-item">
                  <div 
                    className="result-header"
                    onClick={() => toggleExpanded(result.name)}
                  >
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <FolderOpen size={16} />
                    <div className="result-info">
                      <div className="result-name">{result.name}</div>
                      <div className="result-meta">{formatTimestamp(result.timestamp)}</div>
                    </div>
                    <span className="plot-count">{result.plots.length} plots</span>
                  </div>
                  
                  {isExpanded && (
                    <div className="result-plots">
                      {Object.entries(groupedPlots).map(([category, plots]) => (
                        <div key={category} className="plot-category">
                          <div className="category-header">
                            {getCategoryIcon(category)}
                            <span>{category}</span>
                          </div>
                          <div className="category-plots">
                            {plots.map(plot => (
                              <div
                                key={plot.path}
                                className={`plot-item ${selectedPlot?.path === plot.path ? 'selected' : ''}`}
                                onClick={() => setSelectedPlot(plot)}
                              >
                                <Image size={12} />
                                <span>{plot.name}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="results-viewer">
        {selectedPlot ? (
          <>
            <div className="viewer-header">
              <h3>{selectedPlot.name}</h3>
              <span className="plot-category-badge">{selectedPlot.category}</span>
            </div>
            <div className="viewer-content">
              <img 
                src={`${API_BASE_URL}/api/results/plot/${selectedPlot.path}`}
                alt={selectedPlot.name}
                className="plot-image"
              />
            </div>
          </>
        ) : (
          <div className="viewer-empty">
            <Image size={64} />
            <p>Select a plot to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ResultsExplorer;

