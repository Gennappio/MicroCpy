import { useMemo, useState, useCallback } from 'react';
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  SlidersHorizontal,
  Layers,
  Workflow,
  Plus,
  Trash2,
} from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './ParametersDashboard.css';

const PARAM_NODE_TYPES = new Set(['parameterNode', 'listParameterNode', 'dictParameterNode']);

/**
 * ParametersDashboard - Centralized view of all connected parameter nodes
 * across all subworkflows, with inline editing.
 */
function ParametersDashboard({ overrideData, onUpdateParam }) {
  const {
    workflow,
    stageNodes,
    stageEdges,
    setStageNodes,
    setCurrentMainTab,
    setCurrentStage,
  } = useWorkflowStore();

  // Collapsible state — all expanded by default
  const [collapsedKinds, setCollapsedKinds] = useState(new Set());
  const [collapsedStages, setCollapsedStages] = useState(new Set());
  const [collapsedFunctions, setCollapsedFunctions] = useState(new Set());

  const toggleSet = useCallback((setter, key) => {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Derive all connected parameters from stageNodes + stageEdges
  const groupedParams = useMemo(() => {
    const result = { composer: {}, subworkflow: {} };

    for (const stageName of Object.keys(stageNodes)) {
      const nodes = stageNodes[stageName] || [];
      const edges = stageEdges[stageName] || [];

      const kind =
        workflow.metadata?.gui?.subworkflow_kinds?.[stageName] ||
        (stageName === 'main' ? 'composer' : 'subworkflow');

      // Build a quick node lookup
      const nodeById = {};
      for (const n of nodes) nodeById[n.id] = n;

      // Find edges where source is a param node and target is a function
      for (const edge of edges) {
        const sourceNode = nodeById[edge.source];
        const targetNode = nodeById[edge.target];
        if (!sourceNode || !targetNode) continue;
        if (!PARAM_NODE_TYPES.has(sourceNode.type)) continue;
        if (targetNode.type !== 'workflowFunction') continue;

        const targetHandle = edge.targetHandle || '';
        if (!targetHandle.startsWith('param-')) continue;

        const paramName = targetHandle.replace('param-', '');

        const entry = {
          stageName,
          functionNodeId: targetNode.id,
          functionLabel: targetNode.data?.label || targetNode.id,
          functionName: targetNode.data?.functionName || '',
          paramNodeId: sourceNode.id,
          paramNodeType: sourceNode.type,
          paramName,
          paramNodeData: sourceNode.data,
        };

        if (!result[kind]) result[kind] = {};
        if (!result[kind][stageName]) result[kind][stageName] = {};
        const funcKey = targetNode.id;
        if (!result[kind][stageName][funcKey]) {
          result[kind][stageName][funcKey] = {
            functionLabel: entry.functionLabel,
            functionName: entry.functionName,
            params: [],
          };
        }
        result[kind][stageName][funcKey].params.push(entry);
      }
    }

    return result;
  }, [stageNodes, stageEdges, workflow.metadata]);

  // Count total parameters
  const totalParams = useMemo(() => {
    let count = 0;
    for (const kind of Object.values(groupedParams)) {
      for (const stage of Object.values(kind)) {
        for (const func of Object.values(stage)) {
          count += func.params.length;
        }
      }
    }
    return count;
  }, [groupedParams]);

  // Update a parameterNode's data
  const updateParamNodeData = useCallback(
    (stageName, paramNodeId, updater) => {
      if (onUpdateParam) {
        // Planner mode: delegate to parent (never touches canvas)
        onUpdateParam(paramNodeId, updater);
        return;
      }
      const nodes = stageNodes[stageName] || [];
      const updatedNodes = nodes.map((n) => {
        if (n.id !== paramNodeId) return n;
        return { ...n, data: updater(n.data) };
      });
      setStageNodes(stageName, updatedNodes);
    },
    [stageNodes, setStageNodes, onUpdateParam]
  );

  // Navigate to canvas
  const goToCanvas = useCallback(
    (kind, stageName) => {
      setCurrentMainTab(kind === 'composer' ? 'composers' : 'subworkflows');
      setCurrentStage(stageName);
    },
    [setCurrentMainTab, setCurrentStage]
  );

  // ===== Inline editors =====

  const renderParameterNodeEditor = (stageName, paramNodeId, data) => {
    const params = data.parameters || {};
    return (
      <div className="param-editor param-editor-simple">
        {Object.entries(params).map(([key, value]) => (
          <div key={key} className="param-field">
            <label className="param-field-label">{key}</label>
            {renderValueInput(value, (newVal) => {
              updateParamNodeData(stageName, paramNodeId, (d) => ({
                ...d,
                parameters: { ...d.parameters, [key]: newVal },
              }));
            })}
          </div>
        ))}
        {Object.keys(params).length === 0 && (
          <span className="param-empty">No parameters defined</span>
        )}
      </div>
    );
  };

  const renderListParameterNodeEditor = (stageName, paramNodeId, data) => {
    const items = data.items || [];
    const listType = data.listType || 'string';
    return (
      <div className="param-editor param-editor-list">
        <div className="param-list-header">
          <span className="param-type-badge list">List ({listType})</span>
          <span className="param-count">{items.length} items</span>
        </div>
        {items.map((item, idx) => (
          <div key={idx} className="param-list-row">
            <span className="param-list-index">{idx}</span>
            {renderValueInput(item, (newVal) => {
              updateParamNodeData(stageName, paramNodeId, (d) => {
                const newItems = [...(d.items || [])];
                newItems[idx] = newVal;
                return { ...d, items: newItems };
              });
            })}
            <button
              className="param-row-action delete"
              onClick={() => {
                updateParamNodeData(stageName, paramNodeId, (d) => {
                  const newItems = [...(d.items || [])];
                  newItems.splice(idx, 1);
                  return { ...d, items: newItems };
                });
              }}
              title="Remove item"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
        <button
          className="param-add-btn"
          onClick={() => {
            updateParamNodeData(stageName, paramNodeId, (d) => {
              const newItems = [...(d.items || [])];
              newItems.push(listType === 'float' ? 0 : '');
              return { ...d, items: newItems };
            });
          }}
        >
          <Plus size={12} /> Add item
        </button>
      </div>
    );
  };

  const renderDictParameterNodeEditor = (stageName, paramNodeId, data) => {
    const entries = data.entries || [];
    return (
      <div className="param-editor param-editor-dict">
        <div className="param-list-header">
          <span className="param-type-badge dict">Dictionary</span>
          <span className="param-count">{entries.length} entries</span>
        </div>
        <div className="param-dict-table">
          {entries.length > 0 && (
            <div className="param-dict-header-row">
              <span>Key</span>
              <span>Type</span>
              <span>Value</span>
              <span></span>
            </div>
          )}
          {entries.map((entry, idx) => (
            <div key={idx} className="param-dict-entry-block">
              <div className="param-dict-row">
                <input
                  className="param-input param-input-key"
                  value={entry.key || ''}
                  onChange={(e) => {
                    updateParamNodeData(stageName, paramNodeId, (d) => {
                      const newEntries = [...(d.entries || [])];
                      newEntries[idx] = { ...newEntries[idx], key: e.target.value };
                      return { ...d, entries: newEntries };
                    });
                  }}
                />
                <select
                  className="param-input param-input-type"
                  value={entry.valueType || 'string'}
                  onChange={(e) => {
                    updateParamNodeData(stageName, paramNodeId, (d) => {
                      const newEntries = [...(d.entries || [])];
                      newEntries[idx] = { ...newEntries[idx], valueType: e.target.value };
                      return { ...d, entries: newEntries };
                    });
                  }}
                >
                  <option value="string">string</option>
                  <option value="float">float</option>
                  <option value="int">int</option>
                  <option value="bool">bool</option>
                  <option value="list">list</option>
                  <option value="dict">dict</option>
                </select>
                {entry.valueType === 'list' || entry.valueType === 'dict' ? (
                  <span className="param-complex-value-placeholder">
                    {entry.valueType === 'list'
                      ? `${Array.isArray(entry.value) ? entry.value.length : 0} items`
                      : 'JSON'}
                  </span>
                ) : (
                  renderValueInput(
                    entry.value,
                    (newVal) => {
                      updateParamNodeData(stageName, paramNodeId, (d) => {
                        const newEntries = [...(d.entries || [])];
                        newEntries[idx] = { ...newEntries[idx], value: newVal };
                        return { ...d, entries: newEntries };
                      });
                    },
                    entry.valueType
                  )
                )}
                <button
                  className="param-row-action delete"
                  onClick={() => {
                    updateParamNodeData(stageName, paramNodeId, (d) => {
                      const newEntries = [...(d.entries || [])];
                      newEntries.splice(idx, 1);
                      return { ...d, entries: newEntries };
                    });
                  }}
                  title="Remove entry"
                >
                  <Trash2 size={12} />
                </button>
              </div>
              {/* Inline sub-editor for list values */}
              {entry.valueType === 'list' && (
                <div className="param-dict-nested-list">
                  {(Array.isArray(entry.value) ? entry.value : []).map((item, itemIdx) => (
                    <div key={itemIdx} className="param-list-row">
                      <span className="param-list-index">{itemIdx}</span>
                      {renderValueInput(item, (newVal) => {
                        updateParamNodeData(stageName, paramNodeId, (d) => {
                          const newEntries = [...(d.entries || [])];
                          const oldList = Array.isArray(newEntries[idx].value)
                            ? [...newEntries[idx].value]
                            : [];
                          oldList[itemIdx] = newVal;
                          newEntries[idx] = { ...newEntries[idx], value: oldList };
                          return { ...d, entries: newEntries };
                        });
                      })}
                      <button
                        className="param-row-action delete"
                        onClick={() => {
                          updateParamNodeData(stageName, paramNodeId, (d) => {
                            const newEntries = [...(d.entries || [])];
                            const oldList = Array.isArray(newEntries[idx].value)
                              ? [...newEntries[idx].value]
                              : [];
                            oldList.splice(itemIdx, 1);
                            newEntries[idx] = { ...newEntries[idx], value: oldList };
                            return { ...d, entries: newEntries };
                          });
                        }}
                        title="Remove item"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                  <button
                    className="param-add-btn"
                    onClick={() => {
                      updateParamNodeData(stageName, paramNodeId, (d) => {
                        const newEntries = [...(d.entries || [])];
                        const oldList = Array.isArray(newEntries[idx].value)
                          ? [...newEntries[idx].value]
                          : [];
                        oldList.push('');
                        newEntries[idx] = { ...newEntries[idx], value: oldList };
                        return { ...d, entries: newEntries };
                      });
                    }}
                  >
                    <Plus size={12} /> Add item
                  </button>
                </div>
              )}
              {/* Inline JSON editor for dict values */}
              {entry.valueType === 'dict' && (
                <div className="param-dict-nested-json">
                  <textarea
                    className="param-input param-input-json"
                    rows={3}
                    value={
                      typeof entry.value === 'object' && entry.value !== null
                        ? JSON.stringify(entry.value, null, 2)
                        : String(entry.value ?? '{}')
                    }
                    onChange={(e) => {
                      const raw = e.target.value;
                      updateParamNodeData(stageName, paramNodeId, (d) => {
                        const newEntries = [...(d.entries || [])];
                        try {
                          newEntries[idx] = { ...newEntries[idx], value: JSON.parse(raw) };
                        } catch {
                          // Keep raw string while user is typing (invalid JSON)
                          newEntries[idx] = { ...newEntries[idx], value: raw };
                        }
                        return { ...d, entries: newEntries };
                      });
                    }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
        <button
          className="param-add-btn"
          onClick={() => {
            updateParamNodeData(stageName, paramNodeId, (d) => {
              const newEntries = [...(d.entries || [])];
              newEntries.push({ key: '', value: '', valueType: 'string' });
              return { ...d, entries: newEntries };
            });
          }}
        >
          <Plus size={12} /> Add entry
        </button>
      </div>
    );
  };

  // Generic value input renderer
  const renderValueInput = (value, onChange, forceType) => {
    const type = forceType || typeof value;

    if (type === 'boolean' || type === 'bool') {
      return (
        <label className="param-checkbox-label">
          <input
            type="checkbox"
            className="param-checkbox"
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span>{value ? 'true' : 'false'}</span>
        </label>
      );
    }

    if (type === 'number' || type === 'float' || type === 'int') {
      return (
        <input
          type="number"
          className="param-input param-input-number"
          value={value ?? ''}
          step={type === 'int' ? 1 : 'any'}
          onChange={(e) => {
            const v = e.target.value;
            if (v === '' || v === '-') {
              onChange(v);
              return;
            }
            onChange(type === 'int' ? parseInt(v, 10) : parseFloat(v));
          }}
        />
      );
    }

    // Default: string
    return (
      <input
        type="text"
        className="param-input param-input-text"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  };

  // Render a single parameter entry
  const renderParamEntry = (entry) => {
    const { stageName, paramNodeId, paramNodeType, paramName } = entry;
    // Use override data if available, otherwise fall back to canvas node data
    const paramNodeData = overrideData ? (overrideData[paramNodeId] || entry.paramNodeData) : entry.paramNodeData;
    return (
      <div key={paramNodeId} className="param-entry">
        <div className="param-entry-header">
          <span className="param-name">{paramNodeData?.label || paramName}</span>
          <span className={`param-node-type-badge ${paramNodeType}`}>
            {paramNodeType === 'parameterNode'
              ? 'params'
              : paramNodeType === 'listParameterNode'
              ? 'list'
              : 'dict'}
          </span>
          <span className="param-target-name">{paramName}</span>
        </div>
        {paramNodeType === 'parameterNode' &&
          renderParameterNodeEditor(stageName, paramNodeId, paramNodeData)}
        {paramNodeType === 'listParameterNode' &&
          renderListParameterNodeEditor(stageName, paramNodeId, paramNodeData)}
        {paramNodeType === 'dictParameterNode' &&
          renderDictParameterNodeEditor(stageName, paramNodeId, paramNodeData)}
      </div>
    );
  };

  // ===== Empty state =====
  if (totalParams === 0) {
    return (
      <div className="parameters-dashboard">
        <div className="parameters-empty">
          <SlidersHorizontal size={48} strokeWidth={1.5} />
          <h2>No Connected Parameters</h2>
          <p>
            This dashboard shows parameter nodes that are connected to function
            nodes via edges. To see parameters here:
          </p>
          <ol>
            <li>Switch to a Composer or Sub-workflow canvas</li>
            <li>Add a parameter node from the palette</li>
            <li>Connect it to a function node's parameter socket</li>
          </ol>
        </div>
      </div>
    );
  }

  // ===== Main render =====
  const kindEntries = [
    { key: 'composer', label: 'Composers', icon: <Layers size={16} />, accent: '#10b981' },
    { key: 'subworkflow', label: 'Sub-workflows', icon: <Workflow size={16} />, accent: '#8b5cf6' },
  ];

  return (
    <div className="parameters-dashboard">
      <div className="parameters-header">
        <SlidersHorizontal size={20} />
        <h2>Parameters Dashboard</h2>
        <span className="parameters-count">{totalParams} parameter node{totalParams !== 1 ? 's' : ''}</span>
      </div>

      <div className="parameters-content">
        {kindEntries.map(({ key: kindKey, label: kindLabel, icon, accent }) => {
          const stages = groupedParams[kindKey];
          if (!stages || Object.keys(stages).length === 0) return null;

          const kindCollapsed = collapsedKinds.has(kindKey);

          return (
            <div key={kindKey} className="param-kind-section" style={{ '--kind-accent': accent }}>
              <div
                className="param-kind-header"
                onClick={() => toggleSet(setCollapsedKinds, kindKey)}
              >
                {kindCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                {icon}
                <span className="param-kind-label">{kindLabel}</span>
              </div>

              {!kindCollapsed &&
                Object.entries(stages).map(([stageName, functions]) => {
                  const stageKey = `${kindKey}:${stageName}`;
                  const stageCollapsed = collapsedStages.has(stageKey);

                  return (
                    <div key={stageName} className="param-stage-section">
                      <div
                        className="param-stage-header"
                        onClick={() => toggleSet(setCollapsedStages, stageKey)}
                      >
                        {stageCollapsed ? (
                          <ChevronRight size={14} />
                        ) : (
                          <ChevronDown size={14} />
                        )}
                        <span className="param-stage-name">{stageName}</span>
                        <button
                          className="param-goto-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            goToCanvas(kindKey, stageName);
                          }}
                          title="Go to canvas"
                        >
                          <ExternalLink size={12} />
                          <span>Go to canvas</span>
                        </button>
                      </div>

                      {!stageCollapsed &&
                        Object.entries(functions).map(([funcId, funcData]) => {
                          const funcKey = `${stageKey}:${funcId}`;
                          const funcCollapsed = collapsedFunctions.has(funcKey);

                          return (
                            <div key={funcId} className="param-function-section">
                              <div
                                className="param-function-header"
                                onClick={() => toggleSet(setCollapsedFunctions, funcKey)}
                              >
                                {funcCollapsed ? (
                                  <ChevronRight size={14} />
                                ) : (
                                  <ChevronDown size={14} />
                                )}
                                <span className="param-function-label">
                                  {funcData.functionLabel}
                                </span>
                                {funcData.functionName && (
                                  <span className="param-function-name">
                                    {funcData.functionName}
                                  </span>
                                )}
                              </div>

                              {!funcCollapsed && (
                                <div className="param-entries">
                                  {funcData.params.map(renderParamEntry)}
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  );
                })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ParametersDashboard;
