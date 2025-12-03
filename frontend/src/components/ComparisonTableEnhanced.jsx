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
        docFilter,
        setDocFilter,
        editingCell,
        setEditingCell,
        editValue,
        setEditValue,
        userCorrections,
        finalJudgments,
        filteredData,
        stats,
        totalTokens,
        handleCellDoubleClick,
        handleCellEditComplete,
        handleFinalJudgmentChange,
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
        if (onSelectAll) onSelectAll(e);
    };

    const handleCellClick = (billingDoc, docType) => {
        if (onViewPDF) {
            onViewPDF(billingDoc, docType);
        }
    };

    const handleFinalJudgment = () => {
        const selectedCount = selectedRows ? selectedRows.size : 0;
        if (selectedCount === 0) {
            alert('최종 판단할 항목을 선택해주세요.');
            return;
        }
        if (window.confirm(`선택된 ${selectedCount}건의 최종 판단을 확정하시겠습니까?`)) {
            const selectedCorrections = {};
            selectedRows.forEach(doc => {
                if (userCorrections[doc]) {
                    selectedCorrections[doc] = userCorrections[doc];
                }
            });
            if (onFinalConfirm) {
                onFinalConfirm(selectedCorrections, Array.from(selectedRows), finalJudgments);
            }
            alert(`✅ ${selectedCount}건의 최종 판단이 확정되었습니다.`);
            if (onSelectAll) onSelectAll({ target: { checked: false } });
        }
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
                onFinalJudgment={handleFinalJudgment}
            />

            <div
                className={`view-mode-${viewMode}`}
                style={{
                    flex: 1,
                    overflow: 'auto',
                    background: 'white',
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

