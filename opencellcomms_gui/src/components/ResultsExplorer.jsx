import { useState, useEffect } from 'react';
import { FolderOpen, Image, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import WorkflowConsole from './WorkflowConsole';
import { API_BASE_URL } from '../apiConfig';
import './ResultsExplorer.css';

function ResultsExplorer() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedResults, setExpandedResults] = useState(new Set());
  const [selectedPlot, setSelectedPlot] = useState(null);
  // Cache-buster for plot images. Must be state bumped on explicit Refresh —
  // an inline Date.now() in the <img> key/src re-downloads the plot on every
  // React render, flooding the backend with connections until the browser
  // exhausts local ports (net::ERR_ADDRESS_INVALID).
  const [imageVersion, setImageVersion] = useState(() => Date.now());

  useEffect(() => {
    loadResults();
  }, []);

  const loadResults = async () => {
    setLoading(true);
    setError('');
    setImageVersion(Date.now());
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

  // A plot's "category" is just the engine's output-folder name (e.g.
  // "subworkflows"), so it only tells the user anything when a run wrote more
  // than one. With a single category it merely repeats itself — hide the
  // category header and the viewer badge in that case.
  const hasMultipleCategories = (plots) =>
    new Set(plots.map(plot => plot.category)).size > 1;

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

  const selectedResult = selectedPlot
    ? results.find(result => result.plots.some(plot => plot.path === selectedPlot.path))
    : null;
  const showCategoryBadge = !!selectedResult && hasMultipleCategories(selectedResult.plots);

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
              const multiCategory = hasMultipleCategories(result.plots);
              
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
                          {multiCategory && (
                            <div className="category-header">
                              {getCategoryIcon(category)}
                              <span>{category}</span>
                            </div>
                          )}
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
              {showCategoryBadge && (
                <span className="plot-category-badge">{selectedPlot.category}</span>
              )}
            </div>
            <div className="viewer-content">
              <img
                src={`${API_BASE_URL}/api/results/plot/${selectedPlot.path}?t=${imageVersion}`}
                alt={selectedPlot.name}
                className="plot-image"
                key={selectedPlot.path}
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

      <div className="results-console">
        <WorkflowConsole workflowName="main" />
      </div>
    </div>
  );
}

export default ResultsExplorer;
