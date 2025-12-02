import React, { useState } from 'react';
import './ComparisonTableEnhanced.css';

const ComparisonTableEnhanced = ({
    data,
    onViewPDF,
    onUpdateField,
    onFinalConfirm,
    selectedRows,
    onRowSelect,
    onSelectAll
}) => {
    const [statusFilter, setStatusFilter] = useState('all');
    const [docFilter, setDocFilter] = useState('');
    const [editingCell, setEditingCell] = useState(null);
    const [editValue, setEditValue] = useState('');
    const [userCorrections, setUserCorrections] = useState({});
    const [finalJudgments, setFinalJudgments] = useState({});

    const getStatusIcon = (status) => {
        switch (status) {
            case 'complete_match': return '✅';
            case 'partial_error': return '⚠️';
            case 'review_required': return '❌';
            default: return '⏳';
        }
    };

    const getConfidenceBadge = (confidence) => {
        if (!confidence && confidence !== 0) return null;
        const pct = (confidence * 100).toFixed(0);
        let colorClass = 'conf-low';
        if (confidence >= 0.9) colorClass = 'conf-high';
        else if (confidence >= 0.7) colorClass = 'conf-mid';
        return <span className={`confidence-badge ${colorClass}`} title={`신뢰도: ${pct}%`}>{pct}%</span>;
    };

    let filteredData = data;
    if (statusFilter !== 'all') {
        filteredData = filteredData.filter(item => {
            const status = item.auto_comparison?.status || item.final_status;
            return status === statusFilter;
        });
    }
    if (docFilter) {
        filteredData = filteredData.filter(item =>
            item.billing_document?.includes(docFilter)
        );
    }

    const stats = {
        total: data.length,
        complete_match: data.filter(d => (d.auto_comparison?.status || d.final_status) === 'complete_match').length,
        partial_error: data.filter(d => (d.auto_comparison?.status || d.final_status) === 'partial_error').length,
        review_required: data.filter(d => (d.auto_comparison?.status || d.final_status) === 'review_required').length,
        corrected: Object.keys(userCorrections).length,
        selected: selectedRows ? selectedRows.size : 0
    };

    const totalTokens = data.reduce((sum, item) => {
        const usage = item.api_usage || {};
        return {
            input: sum.input + (usage.input || 0),
            output: sum.output + (usage.output || 0)
        };
    }, { input: 0, output: 0 });

    const handleRowSelect = (billingDoc) => {
        if (onRowSelect) onRowSelect(billingDoc);
    };

    const handleSelectAll = (e) => {
        if (onSelectAll) onSelectAll(e);
    };

    const handleCellClick = (billingDoc) => {
        if (onViewPDF) {
            onViewPDF(billingDoc);
        }
    };

    const handleCellDoubleClick = (rowIdx, field, currentValue, billingDoc) => {
        setEditingCell({ rowIdx, field, billingDoc, originalValue: currentValue });
        setEditValue(currentValue || '');
    };

    const handleCellEditComplete = (billingDoc, field) => {
        const originalValue = editingCell?.originalValue || '';
        if (editValue !== '' && editValue !== originalValue) {
            setUserCorrections(prev => ({
                ...prev,
                [billingDoc]: {
                    ...(prev[billingDoc] || {}),
                    [field]: editValue
                }
            }));
            if (onUpdateField) {
                onUpdateField(billingDoc, field, editValue);
            }
        }
        setEditingCell(null);
        setEditValue('');
    };

    const handleFinalJudgmentChange = (billingDoc, value) => {
        setFinalJudgments(prev => ({
            ...prev,
            [billingDoc]: value
        }));
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

    const getCorrectedValue = (billingDoc, field, ocrValue) => {
        return userCorrections[billingDoc]?.[field] || ocrValue;
    };

    const formatAmount = (val) => {
        if (val === null || val === undefined || val === '') return '';
        const num = parseFloat(val);
        if (isNaN(num)) return val;
        return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const renderValue = (val, isAmount = false) => {
        if (val === null || val === undefined) return '';
        if (typeof val === 'object') {
            if (val.value !== undefined) {
                const displayVal = isAmount ? formatAmount(val.value) : val.value;
                return `${displayVal} ${val.unit || val.currency || ''}`;
            }
            return JSON.stringify(val);
        }
        return isAmount ? formatAmount(val) : val;
    };

    const headerStyle = {
        padding: '0.4rem 0.3rem',
        textAlign: 'center',
        border: '1px solid #cbd5e1',
        fontWeight: '600',
        fontSize: '0.75rem',
        color: '#475569',
        background: '#f1f5f9'
    };

    const subHeaderStyle = {
        padding: '0.4rem 0.3rem',
        textAlign: 'center',
        border: '1px solid #cbd5e1',
        fontWeight: '500',
        fontSize: '0.7rem',
        color: '#64748b',
        background: '#f8fafc'
    };

    const cellStyle = {
        padding: '0.3rem 0.4rem',
        border: '1px solid #e2e8f0',
        textAlign: 'center',
        fontSize: '0.8rem',
        color: '#1e293b',
        background: 'white'
    };

    const filterSelectStyle = {
        marginTop: '0.25rem',
        padding: '0.2rem 0.3rem',
        fontSize: '0.7rem',
        border: '1px solid #cbd5e1',
        borderRadius: '4px',
        width: '100%',
        maxWidth: '100px'
    };

    const filterInputStyle = {
        marginTop: '0.25rem',
        padding: '0.2rem 0.3rem',
        fontSize: '0.7rem',
        border: '1px solid #cbd5e1',
        borderRadius: '4px',
        width: '100%',
        maxWidth: '100px'
    };

    return (
        <div className="comparison-enhanced-container">
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.75rem 1rem',
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                marginBottom: '0.5rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h4 style={{ margin: 0, fontSize: '0.95rem' }}>1차 대사 결과</h4>
                    <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <span className="stat-badge">전체: {stats.total}</span>
                        <span className="stat-badge stat-match">✅ {stats.complete_match}</span>
                        <span className="stat-badge stat-warning">⚠️ {stats.partial_error}</span>
                        <span className="stat-badge stat-error">❌ {stats.review_required}</span>
                        {stats.corrected > 0 && (
                            <span className="stat-badge" style={{ background: '#dbeafe', color: '#1e40af' }}>
                                ✏️ 수정: {stats.corrected}
                            </span>
                        )}
                        {stats.selected > 0 && (
                            <span className="stat-badge" style={{ background: '#fef3c7', color: '#92400e' }}>
                                ☑️ 선택: {stats.selected}
                            </span>
                        )}
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                        📊 토큰: <span style={{ fontWeight: '600' }}>📥 {totalTokens.input.toLocaleString()}</span> / <span style={{ fontWeight: '600' }}>📤 {totalTokens.output.toLocaleString()}</span>
                    </div>
                    <button
                        onClick={handleFinalJudgment}
                        disabled={selectedRows.size === 0}
                        style={{
                            padding: '0.5rem 1rem',
                            background: selectedRows.size > 0 ? '#10b981' : '#cbd5e1',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '0.9rem',
                            fontWeight: '600',
                            cursor: selectedRows.size > 0 ? 'pointer' : 'not-allowed'
                        }}
                    >
                        ✔️ 선택 항목 최종 판단 ({selectedRows.size})
                    </button>
                </div>
            </div>

            <div style={{
                flex: 1,
                overflow: 'auto',
                background: 'white',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
            }}>
                <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '0.8rem'
                }}>
                    <colgroup>
                        <col style={{ width: '40px' }} />
                        <col style={{ width: '60px' }} />
                        <col style={{ width: '80px' }} />
                        <col style={{ width: '100px' }} />
                        <col style={{ width: '100px' }} />
                        <col style={{ width: '100px' }} />
                        <col style={{ width: '50px' }} />
                        <col style={{ width: '80px' }} />
                        <col style={{ width: '50px' }} />
                        <col style={{ width: '120px' }} />
                        <col style={{ width: '120px' }} />
                        <col style={{ width: '100px' }} />
                        <col style={{ width: '50px' }} />
                        <col style={{ width: '100px' }} />
                        <col style={{ width: '100px' }} />
                        <col style={{ width: '50px' }} />
                        <col style={{ width: '120px' }} />
                    </colgroup>
                    <thead style={{
                        position: 'sticky',
                        top: 0,
                        background: '#f8fafc',
                        zIndex: 10
                    }}>
                        <tr>
                            <th rowSpan="2" style={headerStyle}>
                                <input
                                    type="checkbox"
                                    checked={filteredData.length > 0 && selectedRows.size === filteredData.length}
                                    onChange={handleSelectAll}
                                    style={{ cursor: 'pointer', transform: 'scale(1.1)' }}
                                />
                            </th>
                            <th rowSpan="2" style={headerStyle}>
                                <div>1차 판단</div>
                                <select
                                    value={statusFilter}
                                    onChange={(e) => setStatusFilter(e.target.value)}
                                    style={filterSelectStyle}
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    <option value="all">전체</option>
                                    <option value="complete_match">✅ 일치</option>
                                    <option value="partial_error">⚠️ 부분오류</option>
                                    <option value="review_required">❌ 검토필요</option>
                                </select>
                            </th>
                            <th rowSpan="2" style={headerStyle}>최종 판단</th>
                            <th rowSpan="2" style={headerStyle}>
                                <div>전표번호</div>
                                <input
                                    type="text"
                                    value={docFilter}
                                    onChange={(e) => setDocFilter(e.target.value)}
                                    placeholder="검색..."
                                    style={filterInputStyle}
                                    onClick={(e) => e.stopPropagation()}
                                />
                            </th>
                            <th colSpan="5" style={{ ...headerStyle, background: '#f1f5f9', color: '#475569' }}>전표 데이터</th>
                            <th colSpan="4" style={{ ...headerStyle, background: '#fdf2f8', color: '#db2777' }}>Invoice 추출</th>
                            <th colSpan="3" style={{ ...headerStyle, background: '#eff6ff', color: '#2563eb' }}>BL 추출</th>
                            <th rowSpan="2" style={headerStyle}>토큰</th>
                        </tr>
                        <tr>
                            <th style={subHeaderStyle}>선적일</th>
                            <th style={subHeaderStyle}>금액</th>
                            <th style={subHeaderStyle}>통화</th>
                            <th style={subHeaderStyle}>수량</th>
                            <th style={subHeaderStyle}>Inco</th>
                            <th style={subHeaderStyle}>날짜</th>
                            <th style={subHeaderStyle}>금액</th>
                            <th style={subHeaderStyle}>수량</th>
                            <th style={subHeaderStyle}>Inco</th>
                            <th style={subHeaderStyle}>수량</th>
                            <th style={subHeaderStyle}>선적일</th>
                            <th style={subHeaderStyle}>Inco</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredData.map((row, idx) => {
                            const status = row.auto_comparison?.status || row.final_status || 'unknown';
                            const fieldResults = row.auto_comparison?.field_results || {};
                            const apiUsage = row.api_usage || { input: 0, output: 0 };
                            const step1 = row.step1_data || {};
                            const ocr = row.ocr_data || {};
                            const blData = row.bl_data || {};
                            const billingDoc = row.billing_document;
                            const isSelected = selectedRows.has(billingDoc);

                            const dateValue = getCorrectedValue(billingDoc, 'date', ocr.date);
                            const amountValue = getCorrectedValue(billingDoc, 'amount', ocr.amount);
                            const quantityValue = getCorrectedValue(billingDoc, 'quantity', ocr.quantity);
                            const incotermsValue = getCorrectedValue(billingDoc, 'incoterms', ocr.incoterms);

                            const isDateCorrected = userCorrections[billingDoc]?.date;
                            const isAmountCorrected = userCorrections[billingDoc]?.amount;
                            const isQuantityCorrected = userCorrections[billingDoc]?.quantity;
                            const isIncotermsCorrected = userCorrections[billingDoc]?.incoterms;

                            return (
                                <tr key={idx} style={{
                                    borderBottom: '1px solid #e2e8f0',
                                    background: isSelected ? '#fef3c7' : 'white'
                                }}>
                                    <td style={cellStyle}>
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => handleRowSelect(billingDoc)}
                                            style={{ cursor: 'pointer', transform: 'scale(1.1)' }}
                                        />
                                    </td>
                                    <td style={cellStyle}>{getStatusIcon(status)}</td>
                                    <td style={cellStyle}>
                                        <select
                                            value={finalJudgments[billingDoc] || ''}
                                            onChange={(e) => handleFinalJudgmentChange(billingDoc, e.target.value)}
                                            style={{
                                                padding: '0.2rem',
                                                border: '1px solid #cbd5e1',
                                                borderRadius: '4px',
                                                fontSize: '0.75rem',
                                                cursor: 'pointer',
                                                background: finalJudgments[billingDoc] === 'match' ? '#d1fae5' :
                                                    finalJudgments[billingDoc] === 'mismatch' ? '#fee2e2' : 'white'
                                            }}
                                        >
                                            <option value="">-</option>
                                            <option value="match">✅</option>
                                            <option value="mismatch">❌</option>
                                        </select>
                                    </td>
                                    <td style={{ ...cellStyle, fontWeight: '600', background: '#f8fafc' }}>{billingDoc}</td>

                                    {/* 전표 데이터 */}
                                    <td style={cellStyle}>{step1.shipment_date || step1.date || '-'}</td>
                                    <td style={cellStyle}>{step1.amount || '-'}</td>
                                    <td style={cellStyle}>{step1.currency || '-'}</td>
                                    <td style={cellStyle}>{renderValue(step1.quantity) || '-'}</td>
                                    <td style={cellStyle}>{step1.incoterms || '-'}</td>

                                    {/* Invoice 추출 */}
                                    <td
                                        style={{
                                            ...cellStyle,
                                            cursor: editingCell?.rowIdx === idx && editingCell?.field === 'date' ? 'text' : 'pointer',
                                            background: isDateCorrected ? '#dbeafe' : (fieldResults.date?.match ? '#d1fae5' : '#fee2e2')
                                        }}
                                        onClick={() => handleCellClick(billingDoc)}
                                        onDoubleClick={() => handleCellDoubleClick(idx, 'date', dateValue, billingDoc)}
                                        title={isDateCorrected ? "수정됨" : "클릭: PDF | 더블클릭: 수정"}
                                    >
                                        {editingCell?.rowIdx === idx && editingCell?.field === 'date' ? (
                                            <input
                                                type="text"
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                onBlur={() => handleCellEditComplete(billingDoc, 'date')}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleCellEditComplete(billingDoc, 'date');
                                                    if (e.key === 'Escape') setEditingCell(null);
                                                }}
                                                autoFocus
                                                style={{ width: '100%', padding: '0.2rem', border: '2px solid #3b82f6' }}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        ) : (
                                            <>
                                                {renderValue(dateValue) || '-'} {getConfidenceBadge(fieldResults.date?.confidence)}
                                                {isDateCorrected && <span style={{ marginLeft: '0.2rem', color: '#1e40af' }}>✏️</span>}
                                            </>
                                        )}
                                    </td>

                                    <td
                                        style={{
                                            ...cellStyle,
                                            cursor: editingCell?.rowIdx === idx && editingCell?.field === 'amount' ? 'text' : 'pointer',
                                            background: isAmountCorrected ? '#dbeafe' : (fieldResults.amount?.match ? '#d1fae5' : '#fee2e2')
                                        }}
                                        onClick={() => handleCellClick(billingDoc)}
                                        onDoubleClick={() => handleCellDoubleClick(idx, 'amount', amountValue, billingDoc)}
                                    >
                                        {editingCell?.rowIdx === idx && editingCell?.field === 'amount' ? (
                                            <input
                                                type="text"
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                onBlur={() => handleCellEditComplete(billingDoc, 'amount')}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleCellEditComplete(billingDoc, 'amount');
                                                    if (e.key === 'Escape') setEditingCell(null);
                                                }}
                                                autoFocus
                                                style={{ width: '100%', padding: '0.2rem', border: '2px solid #3b82f6' }}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        ) : (
                                            <>
                                                {renderValue(amountValue, true) || '-'} {getConfidenceBadge(fieldResults.amount?.confidence)}
                                                {isAmountCorrected && <span style={{ marginLeft: '0.2rem', color: '#1e40af' }}>✏️</span>}
                                            </>
                                        )}
                                    </td>

                                    <td
                                        style={{
                                            ...cellStyle,
                                            cursor: editingCell?.rowIdx === idx && editingCell?.field === 'quantity' ? 'text' : 'pointer',
                                            background: isQuantityCorrected ? '#dbeafe' : (fieldResults.quantity?.match ? '#d1fae5' : '#fee2e2')
                                        }}
                                        onClick={() => handleCellClick(billingDoc)}
                                        onDoubleClick={() => handleCellDoubleClick(idx, 'quantity', quantityValue, billingDoc)}
                                    >
                                        {editingCell?.rowIdx === idx && editingCell?.field === 'quantity' ? (
                                            <input
                                                type="text"
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                onBlur={() => handleCellEditComplete(billingDoc, 'quantity')}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleCellEditComplete(billingDoc, 'quantity');
                                                    if (e.key === 'Escape') setEditingCell(null);
                                                }}
                                                autoFocus
                                                style={{ width: '100%', padding: '0.2rem', border: '2px solid #3b82f6' }}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        ) : (
                                            <>
                                                {renderValue(quantityValue) || '-'} {getConfidenceBadge(fieldResults.quantity?.confidence)}
                                                {isQuantityCorrected && <span style={{ marginLeft: '0.2rem', color: '#1e40af' }}>✏️</span>}
                                            </>
                                        )}
                                    </td>

                                    <td
                                        style={{
                                            ...cellStyle,
                                            cursor: editingCell?.rowIdx === idx && editingCell?.field === 'incoterms' ? 'text' : 'pointer',
                                            background: isIncotermsCorrected ? '#dbeafe' : (fieldResults.incoterms?.match ? '#d1fae5' : '#fee2e2')
                                        }}
                                        onClick={() => handleCellClick(billingDoc)}
                                        onDoubleClick={() => handleCellDoubleClick(idx, 'incoterms', incotermsValue, billingDoc)}
                                    >
                                        {editingCell?.rowIdx === idx && editingCell?.field === 'incoterms' ? (
                                            <input
                                                type="text"
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                onBlur={() => handleCellEditComplete(billingDoc, 'incoterms')}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleCellEditComplete(billingDoc, 'incoterms');
                                                    if (e.key === 'Escape') setEditingCell(null);
                                                }}
                                                autoFocus
                                                style={{ width: '100%', padding: '0.2rem', border: '2px solid #3b82f6' }}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        ) : (
                                            <>
                                                {renderValue(incotermsValue) || '-'} {getConfidenceBadge(fieldResults.incoterms?.confidence)}
                                                {isIncotermsCorrected && <span style={{ marginLeft: '0.2rem', color: '#1e40af' }}>✏️</span>}
                                            </>
                                        )}
                                    </td>

                                    {/* BL 추출 */}
                                    <td style={cellStyle}>{renderValue(blData.quantity) || '-'}</td>
                                    <td style={cellStyle}>{renderValue(blData.shipment_date) || '-'}</td>
                                    <td style={cellStyle}>{renderValue(blData.incoterms) || '-'}</td>

                                    <td style={{ ...cellStyle, fontSize: '0.7rem', fontFamily: 'monospace' }} title={`예상 비용: $${((apiUsage.input / 1000000 * 0.075 + apiUsage.output / 1000000 * 0.30)).toFixed(4)}`}>
                                        {apiUsage.input || 0}/{apiUsage.output || 0}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ComparisonTableEnhanced;
