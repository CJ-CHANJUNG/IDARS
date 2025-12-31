import React, { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from 'react';
import './LedgerTable.css';

const LedgerTable = forwardRef(({ data, onDataChange, isLoading, visibleColumns, onColumnReorder, isEditMode, headerStyles, columnGroups, onCellClick, getCellClassName, handleDoubleClick }, ref) => {

  useImperativeHandle(ref, () => ({
    getSelectedRows: () => {
      if (selectedRows.size > 0) {
        return Array.from(selectedRows).map(index => filteredData[index]);
      }
      return [];
    },
    clearSelection: () => {
      setSelection(null);
      setSelectedRows(new Set());
    },
    deleteSelectedRows: () => {
      if (selectedRows.size > 0) {
        deleteRows(Array.from(selectedRows));
      }
    },
    insertRowAboveSelection: () => {
      if (selectedRows.size > 0) {
        const indices = Array.from(selectedRows).sort((a, b) => a - b);
        insertRow(indices[0], 0); // Insert above the first selected row
      } else if (selection) {
        const { start, end } = selection;
        const minRow = Math.min(start.row, end.row);
        insertRow(minRow, 0);
      } else {
        // No selection, append to end
        const newRow = {};
        headers.forEach(h => newRow[h] = '');
        onDataChange([...data, newRow]);
      }
    }
  }));

  // Selection State: { start: { row, col }, end: { row, col } }
  // col: -1 for selection column, 0...N-1 for data columns
  const [selection, setSelection] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedRows, setSelectedRows] = useState(new Set()); // Track selected rows for multi-select

  const [draggedColumn, setDraggedColumn] = useState(null);
  const [columnWidths, setColumnWidths] = useState({});
  const [resizingColumn, setResizingColumn] = useState(null);
  const [resizeStartX, setResizeStartX] = useState(null);
  const [resizeStartWidth, setResizeStartWidth] = useState(null);
  const [focusedCell, setFocusedCell] = useState(null);

  // Filter State
  const [filters, setFilters] = useState({}); // { header: Set(selectedValues) }
  const [activeFilterColumn, setActiveFilterColumn] = useState(null); // Column with open dropdown
  const [filterSearchText, setFilterSearchText] = useState(''); // Search text for filter

  // Editing State
  const [contextMenu, setContextMenu] = useState(null); // { x, y, rowIndex }
  const [editingCell, setEditingCell] = useState(null); // { rowIndex, colIndex, value }

  // Use visibleColumns from props, or default to all keys if not provided
  const headers = visibleColumns || (data && data.length > 0 ? Object.keys(data[0]) : []);

  // Initialize column widths
  useEffect(() => {
    if (headers.length > 0 && Object.keys(columnWidths).length === 0) {
      const initialWidths = {};
      headers.forEach(header => {
        initialWidths[header] = 150;
      });
      setColumnWidths(initialWidths);
    }
  }, [headers]);

  // --- Filtering Logic ---
  const getUniqueValues = (column) => {
    if (!data) return [];
    const values = new Set(data.map(row => row[column] !== null && row[column] !== undefined ? String(row[column]) : '(Blanks)'));
    return Array.from(values).sort();
  };

  const filteredData = React.useMemo(() => {
    if (!data) return [];
    return data.filter(row => {
      return headers.every(header => {
        const selectedValues = filters[header];
        if (!selectedValues || selectedValues.size === 0) return true; // No filter applied

        const cellValue = row[header] !== null && row[header] !== undefined ? String(row[header]) : '(Blanks)';
        return selectedValues.has(cellValue);
      });
    });
  }, [data, filters, headers]);

  const handleFilterChange = (header, value) => {
    setFilters(prev => {
      const currentSet = new Set(prev[header] || []);
      if (currentSet.has(value)) {
        currentSet.delete(value);
      } else {
        currentSet.add(value);
      }

      if (currentSet.size === 0) {
        const newFilters = { ...prev };
        delete newFilters[header];
        return newFilters;
      }

      return { ...prev, [header]: currentSet };
    });
  };

  const handleSelectAllFilter = (header, allValues) => {
    setFilters(prev => {
      const currentSet = prev[header] || new Set();
      const allSelected = allValues.every(val => currentSet.has(val));

      if (allSelected) {
        const newSet = new Set(currentSet);
        allValues.forEach(val => newSet.delete(val));

        if (newSet.size === 0) {
          const newFilters = { ...prev };
          delete newFilters[header];
          return newFilters;
        }
        return { ...prev, [header]: newSet };
      } else {
        const newSet = new Set(currentSet);
        allValues.forEach(val => newSet.add(val));
        return { ...prev, [header]: newSet };
      }
    });
  };

  const clearFilter = (header) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      delete newFilters[header];
      return newFilters;
    });
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (activeFilterColumn && !event.target.closest('.filter-dropdown') && !event.target.closest('.filter-icon')) {
        setActiveFilterColumn(null);
        setFilterSearchText(''); // Reset search on close
      }
      if (contextMenu && !event.target.closest('.context-menu')) {
        setContextMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [activeFilterColumn, contextMenu]);


  // --- Selection Logic ---

  const handleGlobalClick = (e) => {
    // Clear selection if clicking outside table body/header
    // Also check if clicking inside table-container to prevent clearing when dragging ends slightly off-cell
    if (!e.target.closest('td') && !e.target.closest('th') && !e.target.closest('.context-menu') && !e.target.closest('.table-container')) {
      setSelection(null);
      setSelectedRows(new Set());
    }
  };

  const handleMouseDown = (rowIndex, colIndex, e) => {
    if (e.button === 2) { // Right click
      if (rowIndex !== -1) {
        if (isEditMode) {
          setContextMenu({ x: e.clientX, y: e.clientY, rowIndex });
        }
        if (!isRowSelected(rowIndex)) {
          setSelection({
            start: { row: rowIndex, col: -1 },
            end: { row: rowIndex, col: headers.length - 1 }
          });
          // Update selectedRows for multi-select consistency
          setSelectedRows(new Set([rowIndex]));
        }
      }
      return;
    }

    if (contextMenu) setContextMenu(null);
    if (editingCell) {
      saveEdit();
    }

    setIsDragging(true);
    setSelection({
      start: { row: rowIndex, col: colIndex },
      end: { row: rowIndex, col: colIndex }
    });
    setFocusedCell({ rowIndex, col: colIndex === -1 ? null : headers[colIndex] });

    // Reset multi-row set on new selection start, unless we implement ctrl-click
    if (colIndex === -1) {
      setSelectedRows(new Set([rowIndex]));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleColumnHeaderClick = (colIndex, e) => {
    if (e.target.closest('.filter-icon') || e.target.closest('.resize-handle')) return;

    if (filteredData.length > 0) {
      setSelection({
        start: { row: 0, col: colIndex },
        end: { row: filteredData.length - 1, col: colIndex }
      });
      setSelectedRows(new Set());
    }
  };

  const handleMouseEnter = (rowIndex, colIndex) => {
    if (isDragging) {
      setSelection(prev => ({
        ...prev,
        end: { row: rowIndex, col: colIndex }
      }));

      // If dragging on row headers, select multiple rows
      if (selection && selection.start.col === -1 && colIndex === -1) {
        const start = Math.min(selection.start.row, rowIndex);
        const end = Math.max(selection.start.row, rowIndex);
        const newSet = new Set();
        for (let i = start; i <= end; i++) newSet.add(i);
        setSelectedRows(newSet);
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => setIsDragging(false);
    window.addEventListener('mouseup', handleGlobalMouseUp);
    // Add global click listener for clearing selection
    window.addEventListener('click', handleGlobalClick);
    return () => {
      window.removeEventListener('mouseup', handleGlobalMouseUp);
      window.removeEventListener('click', handleGlobalClick);
    };
  }, []);

  const handleSelectAll = () => {
    if (!filteredData || filteredData.length === 0) return;
    if (selectedRows.size === filteredData.length) {
      setSelectedRows(new Set());
    } else {
      const allIndices = new Set(filteredData.map((_, idx) => idx));
      setSelectedRows(allIndices);
    }
  };

  const isCellSelected = (rowIndex, colIndex) => {
    if (!selection) return false;
    const { start, end } = selection;
    const minRow = Math.min(start.row, end.row);
    const maxRow = Math.max(start.row, end.row);
    const minCol = Math.min(start.col, end.col);
    const maxCol = Math.max(start.col, end.col);

    return (
      rowIndex >= minRow &&
      rowIndex <= maxRow &&
      colIndex >= minCol &&
      colIndex <= maxCol
    );
  };

  const isRowSelected = (rowIndex) => {
    return selectedRows.has(rowIndex);
  };

  const toggleRowSelection = (rowIndex, e) => {
    e.stopPropagation();
    setSelectedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rowIndex)) {
        newSet.delete(rowIndex);
      } else {
        newSet.add(rowIndex);
      }
      return newSet;
    });
  };


  // --- Editing Logic ---
  const handleEditChange = (e) => {
    setEditingCell(prev => ({ ...prev, value: e.target.value }));
  };

  const saveEdit = () => {
    if (editingCell && onDataChange) {
      const { rowIndex, colIndex, value } = editingCell;
      const header = headers[colIndex];
      const newData = [...data];
      const actualIndex = data.indexOf(filteredData[rowIndex]); // Find index in original data
      if (actualIndex !== -1) {
        newData[actualIndex] = { ...newData[actualIndex], [header]: value };
        onDataChange(newData);
      }
      setEditingCell(null);
    }
  };

  const handleKeyDownEdit = (e) => {
    if (e.key === 'Enter') {
      saveEdit();
    } else if (e.key === 'Escape') {
      setEditingCell(null);
    }
  };

  const insertRow = (rowIndex, offset) => {
    if (!onDataChange) return;
    const newData = [...data];
    const newRow = {};
    headers.forEach(h => newRow[h] = ''); // Initialize with empty strings
    const actualIndex = data.indexOf(filteredData[rowIndex]);
    if (actualIndex !== -1) {
      newData.splice(actualIndex + offset, 0, newRow);
    } else {
      // Fallback if filtered (append?) or insert at end
      newData.push(newRow);
    }
    onDataChange(newData);
    setContextMenu(null);
  };

  const deleteRows = (rowIndices) => {
    if (!onDataChange) return;
    // Sort indices descending to avoid shift issues
    const sortedIndices = [...rowIndices].sort((a, b) => b - a);
    const newData = [...data];
    sortedIndices.forEach(idx => {
      const actualIndex = data.indexOf(filteredData[idx]);
      if (actualIndex !== -1) {
        newData.splice(actualIndex, 1);
      }
    });
    onDataChange(newData);
    setSelectedRows(new Set());
    setSelection(null);
    setContextMenu(null);
  };

  const handleContextMenuAction = (action) => {
    if (!contextMenu) return;
    const { rowIndex } = contextMenu;
    if (action === 'insertAbove') insertRow(rowIndex, 0);
    if (action === 'insertBelow') insertRow(rowIndex, 1);
    if (action === 'delete') {
      if (selectedRows.size > 0) {
        deleteRows(Array.from(selectedRows));
      } else {
        deleteRows([rowIndex]);
      }
    }
  };

  // --- Keyboard Navigation (Basic) ---
  useEffect(() => {
    const handleKeyDown = async (e) => {
      if (editingCell) return; // Let input handle keys

      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (isEditMode && selectedRows.size > 0) {
          deleteRows(Array.from(selectedRows));
        }
        return;
      }

      // Copy
      if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
        if (!selection || !filteredData) return;
        const { start, end } = selection;
        const minRow = Math.min(start.row, end.row);
        const maxRow = Math.max(start.row, end.row);
        let minCol, maxCol;
        if (start.col === -1 || end.col === -1) {
          minCol = 0;
          maxCol = headers.length - 1;
        } else {
          minCol = Math.min(start.col, end.col);
          maxCol = Math.max(start.col, end.col);
        }
        const rows = [];
        for (let i = minRow; i <= maxRow; i++) {
          const rowData = [];
          for (let j = minCol; j <= maxCol; j++) {
            const val = filteredData[i][headers[j]];
            rowData.push(val !== null ? val : '');
          }
          rows.push(rowData.join('\t'));
        }
        const text = rows.join('\n');
        try {
          await navigator.clipboard.writeText(text);
        } catch (err) {
          console.error('Failed to copy:', err);
        }
      }
    };

    const handlePaste = async (e) => {
      if (!selection || !onDataChange) return;
      if (!isEditMode) return;

      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData).getData('text');
      const rows = text.split(/\r\n|\n|\r/).map(row => row.split('\t'));

      if (rows.length === 0) return;

      const { start } = selection;
      const startRowIndex = start.row;
      const startColIndex = start.col === -1 ? 0 : start.col;

      const newData = [...data];

      rows.forEach((rowValues, i) => {
        const targetRowIndex = startRowIndex + i;

        if (targetRowIndex >= newData.length) {
          const newRow = {};
          headers.forEach(h => newRow[h] = '');
          newData.push(newRow);
        }

        let actualDataIndex = -1;
        if (targetRowIndex < filteredData.length) {
          actualDataIndex = data.indexOf(filteredData[targetRowIndex]);
        } else {
          actualDataIndex = newData.length - 1;
        }

        if (actualDataIndex !== -1) {
          const rowData = { ...newData[actualDataIndex] };
          rowValues.forEach((val, j) => {
            const targetColIndex = startColIndex + j;
            if (targetColIndex < headers.length) {
              rowData[headers[targetColIndex]] = val;
            }
          });
          newData[actualDataIndex] = rowData;
        }
      });

      onDataChange(newData);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('paste', handlePaste);
    };
  }, [selection, filteredData, headers, data, onDataChange, isEditMode, selectedRows]);


  // Auto-fit Column Width
  const handleAutoFit = (column) => {
    if (!filteredData || filteredData.length === 0) return;

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = '14px Inter, sans-serif';

    let maxWidth = context.measureText(column).width + 32;

    const rowsToCheck = filteredData.slice(0, 100);
    rowsToCheck.forEach(row => {
      const value = row[column] ? String(row[column]) : '';
      const width = context.measureText(value).width + 24;
      if (width > maxWidth) maxWidth = width;
    });

    setColumnWidths(prev => ({
      ...prev,
      [column]: Math.min(maxWidth, 500)
    }));
  };

  // --- Drag & Resize Handlers (Existing) ---
  const handleDragStart = (e, column) => {
    if (e.target.className.includes('resize-handle') || e.target.closest('.filter-icon')) {
      e.preventDefault();
      return;
    }
    setDraggedColumn(column);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, column) => {
    e.preventDefault();
    if (draggedColumn === column) return;
  };

  const handleDrop = (e, targetColumn) => {
    e.preventDefault();
    if (draggedColumn && draggedColumn !== targetColumn) {
      const newOrder = [...headers];
      const draggedIdx = newOrder.indexOf(draggedColumn);
      const targetIdx = newOrder.indexOf(targetColumn);
      newOrder.splice(draggedIdx, 1);
      newOrder.splice(targetIdx, 0, draggedColumn);
      if (onColumnReorder) onColumnReorder(newOrder);
    }
    setDraggedColumn(null);
  };

  const handleResizeStart = (e, column) => {
    e.preventDefault();
    e.stopPropagation();
    setResizingColumn(column);
    setResizeStartX(e.clientX);
    setResizeStartWidth(columnWidths[column] || 150);
    document.body.style.cursor = 'col-resize';
  };

  const handleResizeMove = useCallback((e) => {
    if (resizingColumn) {
      const diff = e.clientX - resizeStartX;
      const newWidth = Math.max(20, resizeStartWidth + diff);
      setColumnWidths(prev => ({ ...prev, [resizingColumn]: newWidth }));
    }
  }, [resizingColumn, resizeStartX, resizeStartWidth]);

  const handleResizeEnd = useCallback(() => {
    if (resizingColumn) {
      setResizingColumn(null);
      setResizeStartX(null);
      setResizeStartWidth(null);
      document.body.style.cursor = 'default';
    }
  }, [resizingColumn]);

  useEffect(() => {
    if (resizingColumn) {
      window.addEventListener('mousemove', handleResizeMove);
      window.addEventListener('mouseup', handleResizeEnd);
    }
    return () => {
      window.removeEventListener('mousemove', handleResizeMove);
      window.removeEventListener('mouseup', handleResizeEnd);
    };
  }, [resizingColumn, handleResizeMove, handleResizeEnd]);

  if (isLoading) return <div className="loading-container"><div className="spinner"></div><p>데이터를 불러오는 중입니다...</p></div>;
  if (!data || data.length === 0) return <div className="empty-state"><p>표시할 데이터가 없습니다.</p></div>;

  return (
    <div className={`dp-table-wrapper ${isEditMode ? 'edit-mode' : ''}`} onContextMenu={(e) => e.preventDefault()}>
      <table className="dp-table dp-table-bordered">
        <thead>
          {columnGroups && columnGroups.length > 0 && (
            <tr className="group-header-row">
              <th className="selection-column-header group-empty-cell"></th>
              {(() => {
                const groupCells = [];
                let currentGroup = null;
                let currentColSpan = 0;

                headers.forEach((header, index) => {
                  const group = columnGroups.find(g => g.columns.includes(header));
                  const groupTitle = group ? group.title : '';
                  const groupStyle = group ? group.style : {};

                  if (currentGroup && currentGroup.title === groupTitle) {
                    currentColSpan++;
                  } else {
                    if (currentGroup) {
                      groupCells.push(
                        <th
                          key={`group-${groupCells.length}`}
                          colSpan={currentColSpan}
                          className="dp-th-group-header"
                          style={{
                            textAlign: 'center',
                            padding: '8px',
                            borderBottom: '1px solid #e0e0e0',
                            borderRight: '1px solid #e0e0e0',
                            fontWeight: '600',
                            backgroundColor: '#f8f9fa',
                            ...currentGroup.style
                          }}
                        >
                          {currentGroup.title}
                        </th>
                      );
                    }
                    currentGroup = { title: groupTitle, style: groupStyle };
                    currentColSpan = 1;
                  }
                });

                if (currentGroup) {
                  groupCells.push(
                    <th
                      key={`group-${groupCells.length}`}
                      colSpan={currentColSpan}
                      className="dp-th-group-header"
                      style={{
                        textAlign: 'center',
                        padding: '8px',
                        borderBottom: '1px solid #e0e0e0',
                        borderRight: '1px solid #e0e0e0',
                        fontWeight: '600',
                        backgroundColor: '#f8f9fa',
                        ...currentGroup.style
                      }}
                    >
                      {currentGroup.title}
                    </th>
                  );
                }
                return groupCells;
              })()}
            </tr>
          )}
          <tr>
            <th
              className={columnGroups && columnGroups.length > 0 ? "dp-th-sub" : ""}
              onClick={handleSelectAll}
              title="Select All"
            >
              {/* Select All Click Area */}
            </th>
            {headers.map((header, colIndex) => {
              const uniqueValues = getUniqueValues(header);
              const filteredUniqueValues = uniqueValues.filter(val =>
                String(val).toLowerCase().includes(filterSearchText.toLowerCase())
              );

              const isFiltered = filters[header] && filters[header].size > 0;

              return (
                <th
                  key={header}
                  draggable={!resizingColumn}
                  onDragStart={(e) => handleDragStart(e, header)}
                  onDragOver={(e) => handleDragOver(e, header)}
                  onDrop={(e) => handleDrop(e, header)}
                  onClick={(e) => handleColumnHeaderClick(colIndex, e)}
                  className={draggedColumn === header ? 'dragging' : ''}
                  style={{
                    width: columnWidths[header],
                    minWidth: columnWidths[header],
                    maxWidth: columnWidths[header],
                    ...(headerStyles && headerStyles[header] ? headerStyles[header] : {})
                  }}
                >
                  <div className="th-content">
                    {header}
                    <div
                      className={`filter-icon ${isFiltered ? 'active' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveFilterColumn(activeFilterColumn === header ? null : header);
                      }}
                    >
                      {isFiltered ? '▼' : '▽'}
                    </div>
                    {activeFilterColumn === header && (
                      <div className="filter-dropdown" onClick={(e) => e.stopPropagation()}>
                        <div className="filter-search">
                          <input
                            type="text"
                            placeholder="Search..."
                            value={filterSearchText}
                            onChange={(e) => setFilterSearchText(e.target.value)}
                            autoFocus
                          />
                        </div>
                        <div className="filter-actions">
                          <button onClick={() => handleSelectAllFilter(header, filteredUniqueValues)}>
                            Select All
                          </button>
                          <button onClick={() => clearFilter(header)}>Clear</button>
                        </div>
                        <div className="filter-list">
                          {filteredUniqueValues.map(val => (
                            <label key={val} className="filter-item">
                              <input
                                type="checkbox"
                                checked={filters[header]?.has(val) || false}
                                onChange={() => handleFilterChange(header, val)}
                              />
                              {val}
                            </label>
                          ))}
                          {filteredUniqueValues.length === 0 && (
                            <div className="no-results">No results found</div>
                          )}
                        </div>
                      </div>
                    )}
                    <div
                      className="resize-handle"
                      onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, header); }}
                      onDoubleClick={(e) => { e.stopPropagation(); handleAutoFit(header); }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                </th>
              );
            })}
          </tr>
        </thead >
        <tbody onMouseLeave={() => isDragging && setIsDragging(false)}>
          {filteredData.map((row, rowIndex) => {
            const rowSelected = isRowSelected(rowIndex);
            return (
              <tr key={rowIndex} className={rowSelected ? 'selected-row' : ''}>
                <td
                  className={`selection-cell ${rowSelected ? 'selected' : ''}`}
                  onMouseDown={(e) => handleMouseDown(rowIndex, -1, e)}
                  onMouseEnter={() => handleMouseEnter(rowIndex, -1)}
                  onContextMenu={(e) => handleMouseDown(rowIndex, -1, e)}
                >
                  <div className="selection-cell-content">
                    <span className="row-number">{rowIndex + 1}</span>
                    {isEditMode && (
                      <>
                        <input
                          type="checkbox"
                          className="row-checkbox"
                          checked={rowSelected}
                          onChange={(e) => toggleRowSelection(rowIndex, e)}
                          onClick={(e) => e.stopPropagation()}
                          onMouseDown={(e) => e.stopPropagation()}
                        />
                        <div className="row-actions">
                          <button
                            className="row-action-btn add"
                            title="Insert Row Below"
                            onClick={(e) => { e.stopPropagation(); insertRow(rowIndex, 1); }}
                          >
                            +
                          </button>
                          <button
                            className="row-action-btn delete"
                            title="Delete Row"
                            onClick={(e) => { e.stopPropagation(); deleteRows([rowIndex]); }}
                          >
                            🗑️
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </td>
                {headers.map((header, colIndex) => {
                  const isSelected = isCellSelected(rowIndex, colIndex);
                  const isEditing = editingCell && editingCell.rowIndex === rowIndex && editingCell.colIndex === colIndex;

                  // Custom cell class name
                  const customClassName = getCellClassName ? getCellClassName(row, header, rowIndex, colIndex) : '';

                  const isNumeric = /QUANTITY|AMOUNT/i.test(header);

                  return (
                    <td
                      key={`${rowIndex}-${header}`}
                      className={`${isSelected ? 'selected-cell' : ''} ${customClassName}`}
                      onMouseDown={(e) => handleMouseDown(rowIndex, colIndex, e)}
                      onMouseEnter={() => handleMouseEnter(rowIndex, colIndex)}
                      onClick={(e) => onCellClick && onCellClick(row, header, rowIndex, colIndex, e)}
                      onDoubleClick={() => handleDoubleClick && handleDoubleClick(rowIndex, colIndex)}
                      style={{
                        width: columnWidths[header],
                        minWidth: columnWidths[header],
                        maxWidth: columnWidths[header],
                        textAlign: isNumeric ? 'right' : 'left'
                      }}
                      title={row[header]}
                    >
                      {isEditing ? (
                        <input
                          autoFocus
                          className="cell-editor"
                          value={editingCell.value}
                          onChange={handleEditChange}
                          onBlur={saveEdit}
                          onKeyDown={handleKeyDownEdit}
                        />
                      ) : (
                        (() => {
                          const val = row[header];
                          if (val === null || val === undefined) return '-';
                          if (typeof val === 'object') {
                            if (val.value !== undefined && val.unit !== undefined) {
                              return `${val.value} ${val.unit}`;
                            }
                            return JSON.stringify(val);
                          }
                          return val;
                        })()
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table >
      {contextMenu && isEditMode && (
        <div
          className="context-menu"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          <div className="context-menu-item" onClick={() => handleContextMenuAction('insertAbove')}>Insert Row Above</div>
          <div className="context-menu-item" onClick={() => handleContextMenuAction('insertBelow')}>Insert Row Below</div>
          <div className="context-menu-separator"></div>
          <div className="context-menu-item delete" onClick={() => handleContextMenuAction('delete')}>Delete Row</div>
        </div>
      )}
    </div >
  );
});

export default LedgerTable;
