import React from 'react';
import './ComparisonTable.css';

const ComparisonTable = ({ data, onCellClick }) => {
    if (!data || data.length === 0) {
        return (
            <div className="empty-state">
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569' }}>데이터가 없습니다</h4>
                <p style={{ margin: 0 }}>Step 1을 확정하고 데이터 추출을 실행해주세요.</p>
            </div>
        );
    }

    // Helper to check if values match across sources
    const getMatchStatus = (a, b, c) => {
        const values = [a, b, c].filter(v => v && v.trim() !== '');
        if (values.length <= 1) return 'none';
        const allMatch = values.every(v => v === values[0]);
        return allMatch ? 'match' : 'mismatch';
    };

    return (
        <div className="comparison-table-container">
            {/* Legend */}
            <div className="comparison-legend">
                <span className="legend-item source-a">
                    <span className="legend-icon">🔵</span>
                    <strong>A</strong> = 전표데이터 (Ledger)
                </span>
                <span className="legend-item source-b">
                    <span className="legend-icon">🔴</span>
                    <strong>B</strong> = 인보이스 (Invoice)
                </span>
                <span className="legend-item source-c">
                    <span className="legend-icon">🟠</span>
                    <strong>C</strong> = B/L (Bill of Lading)
                </span>
            </div>

            {/* Table */}
            <div className="comparison-table-wrapper">
                <table className="comparison-table">
                    <thead>
                        {/* Main header row */}
                        <tr className="main-header-row">
                            <th rowSpan="2" className="billing-doc-header">
                                Billing Document<br />
                                <span className="header-subtitle">전표번호</span>
                            </th>
                            <th colSpan="3" className="field-group-header">
                                Date<br />
                                <span className="header-subtitle">일자</span>
                            </th>
                            <th colSpan="3" className="field-group-header">
                                Incoterms<br />
                                <span className="header-subtitle">인코텀즈</span>
                            </th>
                            <th colSpan="3" className="field-group-header">
                                Quantity<br />
                                <span className="header-subtitle">수량</span>
                            </th>
                            <th rowSpan="2" className="field-group-header">
                                Sales Unit<br />
                                <span className="header-subtitle">판매단위</span>
                            </th>
                            <th colSpan="2" className="field-group-header">
                                Amount<br />
                                <span className="header-subtitle">금액</span>
                            </th>
                            <th colSpan="2" className="field-group-header">
                                Currency<br />
                                <span className="header-subtitle">통화</span>
                            </th>
                        </tr>

                        {/* Sub-column headers */}
                        <tr className="sub-header-row">
                            {/* Date */}
                            <th className="sub-col source-a-header">A</th>
                            <th className="sub-col source-b-header">B</th>
                            <th className="sub-col source-c-header">C</th>
                            {/* Incoterms */}
                            <th className="sub-col source-a-header">A</th>
                            <th className="sub-col source-b-header">B</th>
                            <th className="sub-col source-c-header">C</th>
                            {/* Quantity */}
                            <th className="sub-col source-a-header">A</th>
                            <th className="sub-col source-b-header">B</th>
                            <th className="sub-col source-c-header">C</th>
                            {/* Amount */}
                            <th className="sub-col source-a-header">A</th>
                            <th className="sub-col source-b-header">B</th>
                            {/* Currency */}
                            <th className="sub-col source-a-header">A</th>
                            <th className="sub-col source-b-header">B</th>
                        </tr>
                    </thead>

                    <tbody>
                        {data.map((row, idx) => {
                            const billingDoc = row['Billing Document'];
                            const { sourceA = {}, sourceB = {}, sourceC = {} } = row;

                            // Match status for each field
                            const dateMatch = getMatchStatus(sourceA.Date, sourceB.Date, sourceC.Date);
                            const incotermsMatch = getMatchStatus(sourceA.Incoterms, sourceB.Incoterms, sourceC.Incoterms);
                            const quantityMatch = getMatchStatus(sourceA.Quantity, sourceB.Quantity, sourceC.Quantity);
                            const amountMatch = getMatchStatus(sourceA.Amount, sourceB.Amount, '');
                            const currencyMatch = getMatchStatus(sourceA.Currency, sourceB.Currency, '');

                            return (
                                <tr key={idx} className={idx % 2 === 0 ? 'even-row' : 'odd-row'}>
                                    <td className="billing-doc-cell">{billingDoc}</td>

                                    {/* Date */}
                                    <td className="data-cell source-a-cell">{sourceA.Date || '-'}</td>
                                    <td
                                        className="data-cell source-b-cell clickable"
                                        onClick={() => sourceB.Date && onCellClick && onCellClick(billingDoc, 'Date', 'Invoice')}
                                        title={sourceB.Date ? 'Click to view Invoice PDF' : ''}
                                    >
                                        {sourceB.Date || '-'}
                                    </td>
                                    <td
                                        className="data-cell source-c-cell clickable"
                                        onClick={() => sourceC.Date && onCellClick && onCellClick(billingDoc, 'Date', 'BL')}
                                        title={sourceC.Date ? 'Click to view B/L PDF' : ''}
                                    >
                                        {sourceC.Date || '-'}
                                    </td>

                                    {/* Incoterms */}
                                    <td className="data-cell source-a-cell">{sourceA.Incoterms || '-'}</td>
                                    <td
                                        className="data-cell source-b-cell clickable"
                                        onClick={() => sourceB.Incoterms && onCellClick && onCellClick(billingDoc, 'Incoterms', 'Invoice')}
                                    >
                                        {sourceB.Incoterms || '-'}
                                    </td>
                                    <td
                                        className="data-cell source-c-cell clickable"
                                        onClick={() => sourceC.Incoterms && onCellClick && onCellClick(billingDoc, 'Incoterms', 'BL')}
                                    >
                                        {sourceC.Incoterms || '-'}
                                    </td>

                                    {/* Quantity */}
                                    <td className="data-cell source-a-cell">{sourceA.Quantity || '-'}</td>
                                    <td
                                        className="data-cell source-b-cell clickable"
                                        onClick={() => sourceB.Quantity && onCellClick && onCellClick(billingDoc, 'Quantity', 'Invoice')}
                                    >
                                        {sourceB.Quantity || '-'}
                                    </td>
                                    <td
                                        className="data-cell source-c-cell clickable"
                                        onClick={() => sourceC.Quantity && onCellClick && onCellClick(billingDoc, 'Quantity', 'BL')}
                                    >
                                        {sourceC.Quantity || '-'}
                                    </td>

                                    {/* Sales Unit */}
                                    <td className="data-cell source-a-cell">{sourceA['Sales Unit'] || '-'}</td>

                                    {/* Amount */}
                                    <td className="data-cell source-a-cell">{sourceA.Amount || '-'}</td>
                                    <td
                                        className="data-cell source-b-cell clickable"
                                        onClick={() => sourceB.Amount && onCellClick && onCellClick(billingDoc, 'Amount', 'Invoice')}
                                    >
                                        {sourceB.Amount || '-'}
                                    </td>

                                    {/* Currency */}
                                    <td className="data-cell source-a-cell">{sourceA.Currency || '-'}</td>
                                    <td
                                        className="data-cell source-b-cell clickable"
                                        onClick={() => sourceB.Currency && onCellClick && onCellClick(billingDoc, 'Currency', 'Invoice')}
                                    >
                                        {sourceB.Currency || '-'}
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

export default ComparisonTable;
