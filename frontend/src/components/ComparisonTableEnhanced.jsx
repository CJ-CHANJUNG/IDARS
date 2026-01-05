import React from 'react';
import { useComparisonTable } from '../hooks/useComparisonTable.jsx';
import ComparisonTableControls from './comparison/ComparisonTableControls';
import ComparisonTableHeader from './comparison/ComparisonTableHeader';
import ComparisonTableRow from './comparison/ComparisonTableRow';
import './ComparisonTableEnhanced.css';

const ComparisonTableEnhanced = ({
    data,
    viewMode = 'basic', // 'basic' or 'detailed'
    onViewPDF,
    onUpdateField,
    onFinalConfirm,
    selectedRows,
    onRowSelect,
    onSelectAll
}) => {
    const {
        statusFilter,
        setStatusFilter,
        finalJudgmentFilter, // ★ NEW
        setFinalJudgmentFilter, // ★ NEW
        docFilter,
        setDocFilter,
        editingCell,
        setEditingCell,
        editValue,
        setEditValue,
        userCorrections,
        finalJudgments,
        pendingJudgments, // ★ NEW: 임시 판단
        confirmPendingJudgments, // ★ NEW: 확정 함수
        filteredData,
        stats,
        totalTokens,
        handleCellDoubleClick,
        handleCellEditComplete,
        handleFinalJudgmentChange,
        handleBulkJudgmentUpdate, // ★ Get bulk handler
        getCorrectedValue,
        getStatusIcon,
        getConfidenceBadge,
        renderValue,
        visibleColumns // Get visible columns based on viewMode
    } = useComparisonTable(data, selectedRows, viewMode);

    const handleRowSelect = (billingDoc) => {
        if (onRowSelect) onRowSelect(billingDoc);
    };

    const handleSelectAll = (e) => {
        if (onSelectAll) {
            if (e.target.checked) {
                // Pass only filtered IDs to the handler
                const filteredIds = filteredData.map(row => row.billing_document);
                onSelectAll(e, filteredIds);
            } else {
                // Uncheck all (or pass empty list if needed, but handler handles unchecked)
                onSelectAll(e);
            }
        }
    };

    // ★ NEW: Filter-based selection
    const handleSelectByStatus = (status) => {
        // Filter documents by status and select them
        const docsToSelect = filteredData
            .filter(row => {
                const rowStatus = row.auto_comparison?.status || row.final_status || 'unknown';
                return rowStatus === status;
            })
            .map(row => row.billing_document);

        if (onRowSelect && docsToSelect.length > 0) {
            // Clear current selection first
            if (onSelectAll) {
                onSelectAll({ target: { checked: false } });
            }
            // Then select filtered items
            setTimeout(() => {
                docsToSelect.forEach(doc => onRowSelect(doc));
            }, 50);
        }
    };

    const handleCellClick = (billingDoc, docType, field, coordinates) => {
        if (onViewPDF) {
            onViewPDF(billingDoc, docType, field, coordinates);
        }
    };

    const handleSaveDraft = () => {
        const pendingCount = Object.keys(pendingJudgments).length;
        if (pendingCount === 0) {
            alert('저장할 변경사항이 없습니다.');
            return;
        }

        // ★ 모든 pending 판단을 finalJudgments로 확정
        confirmPendingJudgments(Object.keys(pendingJudgments));

        // ★ Merge pending with final and save
        const judgmentsToSave = { ...finalJudgments, ...pendingJudgments };

        if (onFinalConfirm) {
            onFinalConfirm({}, Object.keys(pendingJudgments), judgmentsToSave);
        }

        alert(`✅ ${pendingCount}건의 판단이 저장되었습니다.`);
    };

    const onCellEditComplete = (billingDoc, field) => {
        handleCellEditComplete(billingDoc, field, onUpdateField);
    };

    return (
        <div className="comparison-enhanced-container">
            {/* Stats and Controls Panel - Outside table */}
            <ComparisonTableControls
                stats={stats}
                totalTokens={totalTokens}
                selectedRows={selectedRows}
                onSelectAll={handleSelectAll}
                onSelectByStatus={handleSelectByStatus}
                onBulkUpdate={handleBulkJudgmentUpdate}
                filteredData={filteredData}
                onSaveDraft={handleSaveDraft} // ★ NEW: Save Draft handler
                pendingCount={Object.keys(pendingJudgments).length} // ★ NEW: Pending count
            />

            <div
                className={`view-mode-${viewMode}`}
                style={{
                    flex: 1,
                    overflow: 'auto',
                    background: '#ffffff',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    maxHeight: 'calc(100vh - 250px)' // Ensure scrollbar is visible
                }}
            >
                <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '0.8rem'
                }}>
                    {/* Table Column Headers - Inside table */}
                    <ComparisonTableHeader
                        statusFilter={statusFilter}
                        setStatusFilter={setStatusFilter}
                        finalJudgmentFilter={finalJudgmentFilter} // ★ NEW
                        setFinalJudgmentFilter={setFinalJudgmentFilter} // ★ NEW
                        docFilter={docFilter}
                        setDocFilter={setDocFilter}
                        selectedRows={selectedRows}
                        filteredData={filteredData}
                        onSelectAll={handleSelectAll}
                        viewMode={viewMode}
                    />
                    <tbody>
                        {filteredData.map((row, idx) => (
                            <ComparisonTableRow
                                key={idx}
                                row={row}
                                idx={idx}
                                selectedRows={selectedRows}
                                editingCell={editingCell}
                                editValue={editValue}
                                setEditValue={setEditValue}
                                userCorrections={userCorrections}
                                finalJudgments={finalJudgments}
                                pendingJudgments={pendingJudgments} // ★ NEW: 임시 판단 전달
                                onRowSelect={handleRowSelect}
                                onCellClick={handleCellClick}
                                onCellDoubleClick={handleCellDoubleClick}
                                onCellEditComplete={onCellEditComplete}
                                onFinalJudgmentChange={handleFinalJudgmentChange}
                                getCorrectedValue={getCorrectedValue}
                                getStatusIcon={getStatusIcon}
                                getConfidenceBadge={getConfidenceBadge}
                                renderValue={renderValue}
                                viewMode={viewMode}
                            />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ComparisonTableEnhanced;
