import { Plus, X, Edit2 } from 'lucide-react';
import { useState } from 'react';
import './BehaviorTabsBar.css';

/**
 * Shared secondary tab strip for Agents / Environment / Processing views.
 * Renders tabs for each subworkflow (init + behaviors) and an Add button.
 */
const BehaviorTabsBar = ({
  tabs,          // [{ name, label, kind }]
  activeTab,
  onTabClick,
  onAddTab,
  onDeleteTab,
  onRenameTab,
  accentColor,   // CSS color string
  addLabel,
}) => {
  const [renamingTab, setRenamingTab] = useState(null);

  const handleRename = (oldName, newName) => {
    if (newName && newName !== oldName) {
      onRenameTab?.(oldName, newName);
    }
    setRenamingTab(null);
  };

  return (
    <div className="behavior-tabs-bar">
      {tabs.map(({ name, label, deletable = true, phase, phaseLabel }) => (
        <button
          key={name}
          className={`behavior-tab ${activeTab === name ? 'active' : ''}`}
          style={{ '--accent': accentColor }}
          onClick={() => onTabClick(name)}
        >
          {renamingTab === name ? (
            <input
              className="behavior-tab-rename"
              defaultValue={name}
              autoFocus
              onBlur={(e) => handleRename(name, e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRename(name, e.target.value);
                else if (e.key === 'Escape') setRenamingTab(null);
              }}
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span className="behavior-tab-label">{label || name}</span>
          )}

          {phaseLabel && (
            <span className={`behavior-tab-phase phase-${phase || 'unknown'}`}>
              {phaseLabel}
            </span>
          )}

          {deletable && (
            <span
              className="behavior-tab-action"
              title="Rename"
              onClick={(e) => { e.stopPropagation(); setRenamingTab(name); }}
            >
              <Edit2 size={11} />
            </span>
          )}
          {deletable && onDeleteTab && (
            <span
              className="behavior-tab-action delete"
              title="Delete"
              onClick={(e) => { e.stopPropagation(); onDeleteTab(name); }}
            >
              <X size={12} />
            </span>
          )}
        </button>
      ))}

      <button className="behavior-tab add-tab" onClick={onAddTab} title={addLabel}>
        <Plus size={14} />
        <span>{addLabel}</span>
      </button>
    </div>
  );
};

export default BehaviorTabsBar;
