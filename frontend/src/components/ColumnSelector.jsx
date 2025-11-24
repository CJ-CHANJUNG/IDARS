import React, { useState } from 'react';
import './ColumnSelector.css';

const ColumnSelector = ({ allColumns, visibleColumns, onToggleColumn, onReset }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="column-selector-container">
            <button
                className="settings-button"
                onClick={() => setIsOpen(!isOpen)}
                title="열 설정"
            >
                ⚙️ 열 설정
            </button>

            {isOpen && (
                <>
                    <div className="backdrop" onClick={() => setIsOpen(false)} />
                    <div className="column-selector-panel">
                        <div className="panel-header">
                            <h3>표시할 열 선택</h3>
                            <button className="close-button" onClick={() => setIsOpen(false)}>×</button>
                        </div>
                        <div className="panel-actions">
                            <button className="text-button" onClick={onReset}>기본값으로 초기화</button>
                        </div>
                        <div className="checkbox-list">
                            {allColumns.map((col) => (
                                <label key={col} className="checkbox-item">
                                    <input
                                        type="checkbox"
                                        checked={visibleColumns.includes(col)}
                                        onChange={() => onToggleColumn(col)}
                                    />
                                    <span className="checkbox-label">{col}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default ColumnSelector;
