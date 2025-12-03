import React from 'react';

const ComparisonTableRow = ({
    row,
    idx,
    selectedRows,
    editingCell,
    editValue,
    setEditValue,
    userCorrections,
    finalJudgments,
    onRowSelect,
    onCellClick,
    onCellDoubleClick,
    onCellEditComplete,
    onFinalJudgmentChange,
    getCorrectedValue,
    getStatusIcon,
    getConfidenceBadge,
    renderValue,
    viewMode = 'basic'  // Add viewMode prop
}) => {
    const status = row.auto_comparison?.status || row.final_status || 'unknown';
    const fieldResults = row.auto_comparison?.field_results || {};
    const blResults = row.auto_comparison?.bl_results || {};  // BL 비교 결과 추가
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

    const cellStyle = {
        padding: '0.3rem 0.4rem',
        border: '1px solid #e2e8f0',
        textAlign: 'center',
        fontSize: '0.8rem',
        color: '#1e293b',
        background: 'white'
    };

    const renderEditableCell = (field, value, isCorrected, fieldResult, isAmount = false) => {
        const isEditing = editingCell?.rowIdx === idx && editingCell?.field === field;

        return (
            <td
                style={{
                    ...cellStyle,
                    cursor: isEditing ? 'text' : 'pointer',
                    background: isCorrected ? '#dbeafe' : (fieldResult?.match ? '#d1fae5' : '#fee2e2')
                }}
                onClick={() => onCellClick(billingDoc)}
                onDoubleClick={() => onCellDoubleClick(idx, field, value, billingDoc)}
                title={isCorrected ? "수정됨" : "클릭: PDF | 더블클릭: 수정"}
            >
                {isEditing ? (
                    <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => onCellEditComplete(billingDoc, field)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') onCellEditComplete(billingDoc, field);
                            if (e.key === 'Escape') onCellEditComplete(billingDoc, field);
                        }}
                        autoFocus
                        style={{ width: '100%', padding: '0.2rem', border: '2px solid #3b82f6' }}
                        onClick={(e) => e.stopPropagation()}
                    />
                ) : (
                    <>
                        {renderValue(value, isAmount) || '-'} {getConfidenceBadge(fieldResult?.confidence)}
                        {isCorrected && <span style={{ marginLeft: '0.2rem', color: '#1e40af' }}>✏️</span>}
                    </>
                )}
            </td>
        );
    };

    return (
        <tr style={{
            borderBottom: '1px solid #e2e8f0',
            background: isSelected ? '#fef3c7' : 'white'
        }}>
            <td style={cellStyle}>
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onRowSelect(billingDoc)}
                    style={{ cursor: 'pointer', transform: 'scale(1.1)' }}
                />
            </td>
            <td style={cellStyle}>{getStatusIcon(status)}</td>
            <td style={cellStyle}>
                <select
                    value={finalJudgments[billingDoc] || ''}
                    onChange={(e) => onFinalJudgmentChange(billingDoc, e.target.value)}
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

            {/* Invoice 추출 - Basic */}
            {renderEditableCell('date', dateValue, isDateCorrected, fieldResults.date)}
            {renderEditableCell('amount', amountValue, isAmountCorrected, fieldResults.amount, true)}
            {renderEditableCell('quantity', quantityValue, isQuantityCorrected, fieldResults.quantity)}
            {renderEditableCell('incoterms', incotermsValue, isIncotermsCorrected, fieldResults.incoterms)}

            {/* Invoice 추출 - Detailed Only */}
            {viewMode === 'detailed' && (
                <>
                    <td style={cellStyle}>{ocr.item_description || '-'}</td>
                    <td style={cellStyle}>{ocr.seller || '-'}</td>
                    <td style={cellStyle}>{ocr.buyer || '-'}</td>
                    <td style={cellStyle}>{ocr.vessel_name || '-'}</td>
                    <td style={cellStyle}>{ocr.port_of_loading || '-'}</td>
                    <td style={cellStyle}>{ocr.port_of_discharge || '-'}</td>
                </>
            )}

            {/* BL 추출 - Basic */}
            <td style={{
                ...cellStyle,
                cursor: 'pointer',
                background: blResults.bl_net_weight?.match ? '#d1fae5' : (blResults.bl_net_weight?.match === false ? '#fee2e2' : cellStyle.background)
            }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>
                {renderValue(blData.net_weight || blData.quantity) || '-'}
            </td>
            <td style={{
                ...cellStyle,
                cursor: 'pointer',
                background: blResults.bl_on_board_date?.match ? '#d1fae5' : (blResults.bl_on_board_date?.match === false ? '#fee2e2' : cellStyle.background)
            }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>
                {renderValue(blData.on_board_date) || '-'}
            </td>
            <td style={{
                ...cellStyle,
                cursor: 'pointer',
                background: blResults.bl_freight_terms?.match ? '#d1fae5' : (blResults.bl_freight_terms?.match === false ? '#fff7ed' : cellStyle.background)
            }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>
                {renderValue(blData.freight_payment_terms || blData.incoterms) || '-'}
            </td>

            {/* BL 추출 - Detailed Only */}
            {viewMode === 'detailed' && (
                <>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.item_description || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.bl_number || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.vessel_name || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.port_of_loading || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.port_of_discharge || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.shipper || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{blData.consignee || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer', background: '#f0f9ff' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{renderValue(blData.net_weight) || '-'}</td>
                    <td style={{ ...cellStyle, cursor: 'pointer' }} onClick={() => onCellClick(row.billing_document, 'Bill_of_Lading')}>{renderValue(blData.gross_weight) || '-'}</td>
                </>
            )}

            <td style={{ ...cellStyle, fontSize: '0.7rem', fontFamily: 'monospace', whiteSpace: 'normal' }}>
                <div>{apiUsage.input || 0}/{apiUsage.output || 0}</div>
                <div style={{ fontSize: '0.6rem', color: '#64748b', marginTop: '2px' }}>
                    ${((apiUsage.input / 1000000 * 0.075) + (apiUsage.output / 1000000 * 0.30)).toFixed(4)}
                </div>
            </td>
        </tr>
    );
};

export default ComparisonTableRow;
