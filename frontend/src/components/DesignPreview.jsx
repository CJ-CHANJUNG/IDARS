import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import './DesignPreview.css';

const DesignPreview = () => {
    const { ledgerData, evidenceData, comparisonResults, project } = useProject();
    const [activeTab, setActiveTab] = useState('step3'); // Default to Step 3 for review
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedRows, setSelectedRows] = useState(new Set());

    // Step 3 Selection States
    const [step3Filter, setStep3Filter] = useState('all');

    // --- Number Formatting Helper ---
    const formatNumber = (value) => {
        if (value === undefined || value === null || value === '') return '-';
        const num = parseFloat(value.toString().replace(/,/g, ''));
        if (isNaN(num)) return value;
        return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    // --- Step 1 Helpers ---
    const getStep1Columns = () => {
        if (ledgerData && ledgerData.length > 0) return Object.keys(ledgerData[0]);
        return ['Posting Date', 'Document Number', 'Vendor Name', 'Amount in doc. curr.', 'Document Currency', 'Purchasing Document', 'Text', 'Reference'];
    };
    const step1Columns = getStep1Columns();

    // --- Step 2 Helpers ---
    const docTypes = [
        { key: 'Bill_of_Lading', label: 'Bill of Lading' },
        { key: 'Commercial_Invoice', label: 'Commercial Invoice' },
        { key: 'Packing_List', label: 'Packing List' },
        { key: 'Weight_List', label: 'Weight List' },
        { key: 'Mill_Certificate', label: 'Mill Certificate' },
        { key: 'Cargo_Insurance', label: 'Cargo Insurance' },
        { key: 'Certificate_Origin', label: 'Certificate of Origin' },
        { key: 'Customs_clearance_Letter', label: 'Customs Clearance Letter' },
        { key: 'Other', label: 'Other' },
    ];

    // --- Dashboard Helpers ---
    const getDashboardSummary = () => {
        if (!comparisonResults) return { total: 0, matched: 0, mismatched: 0, missing: 0 };
        const total = comparisonResults.length;
        const matched = comparisonResults.filter(r => r.auto_comparison?.status === 'match').length;
        const mismatched = comparisonResults.filter(r => r.auto_comparison?.status === 'mismatch').length;
        const missing = total - matched - mismatched;
        return { total, matched, mismatched, missing };
    };
    const dashboardSummary = getDashboardSummary();

    return (
        <div className="design-preview-container">
            <div className="preview-header">
                <h2>Design System Preview (Staging)</h2>
                <p>Live implementation using real project data. This view reflects the exact structure and complexity of the workspace.</p>
            </div>

            <div className="preview-tabs">
                <button
                    className={`preview-tab ${activeTab === 'step1' ? 'active' : ''}`}
                    onClick={() => setActiveTab('step1')}
                >
                    Step 1: Invoice Confirmation
                </button>
                <button
                    className={`preview-tab ${activeTab === 'step2' ? 'active' : ''}`}
                    onClick={() => setActiveTab('step2')}
                >
                    Step 2: Evidence Collection
                </button>
                <button
                    className={`preview-tab ${activeTab === 'step3' ? 'active' : ''}`}
                    onClick={() => setActiveTab('step3')}
                >
                    Step 3: Data Extraction
                </button>
                <button
                    className={`preview-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
                    onClick={() => setActiveTab('dashboard')}
                >
                    📊 Dashboard
                </button>
            </div>

            <div className="preview-content">
                {/* --- STEP 1: INVOICE CONFIRMATION --- */}
                {activeTab === 'step1' && (
                    <div className="dp-card">
                        <div className="dp-toolbar">
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                <button
                                    className={`dp-toggle ${isEditMode ? 'active' : ''}`}
                                    onClick={() => setIsEditMode(!isEditMode)}
                                >
                                    {isEditMode ? '✏️ Edit Mode On' : '✏️ Edit Mode'}
                                </button>
                                <button className="dp-btn dp-btn-secondary">📥 Import Data</button>
                                <button className="dp-btn dp-btn-secondary">➕ Add Row</button>
                                <button className="dp-btn dp-btn-secondary">🗑️ Delete Selected</button>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button className="dp-btn dp-btn-secondary">💾 Save Draft</button>
                                <button className="dp-btn dp-btn-primary">✅ Confirm Invoices</button>
                            </div>
                        </div>
                        <div className="dp-table-wrapper">
                            <table className="dp-table">
                                <thead>
                                    <tr>
                                        <th style={{ width: '40px', textAlign: 'center' }}>
                                            <input type="checkbox" />
                                        </th>
                                        <th style={{ width: '50px', textAlign: 'center' }}>No.</th>
                                        {step1Columns.map(col => (
                                            <th key={col}>{col}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {(ledgerData && ledgerData.length > 0 ? ledgerData : []).map((row, i) => (
                                        <tr key={i}>
                                            <td style={{ textAlign: 'center' }}><input type="checkbox" /></td>
                                            <td style={{ textAlign: 'center', color: '#94a3b8' }}>{i + 1}</td>
                                            {step1Columns.map(col => (
                                                <td key={col} className={col.includes('Amount') || col.includes('Quantity') ? 'dp-text-right' : ''}>
                                                    {col.includes('Amount') || col.includes('Quantity') ? formatNumber(row[col]) : row[col]}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                    {(!ledgerData || ledgerData.length === 0) && (
                                        <tr>
                                            <td colSpan={step1Columns.length + 2} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                                                No data available. Import data to see the preview.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* --- STEP 2: EVIDENCE COLLECTION --- */}
                {activeTab === 'step2' && (
                    <div className="dp-card">
                        <div className="dp-toolbar">
                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <button className="dp-btn dp-btn-primary">📥 Download Evidence</button>
                                <button className="dp-btn dp-btn-secondary">✂️ Split PDF</button>
                            </div>
                            <button className="dp-btn dp-btn-success">✅ Confirm Evidence</button>
                        </div>
                        <div className="dp-table-wrapper">
                            <table className="dp-table">
                                <thead>
                                    <tr>
                                        <th style={{ width: '30px', textAlign: 'center', position: 'sticky', left: 0, zIndex: 30, background: '#f8fafc' }}>
                                            <input type="checkbox" />
                                        </th>
                                        <th style={{ minWidth: '140px', position: 'sticky', left: '30px', zIndex: 30, background: '#f8fafc', borderRight: '1px solid #e2e8f0', fontSize: '0.8rem' }}>Billing Document</th>
                                        <th style={{ textAlign: 'center', width: '60px', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>Evidence</th>
                                        <th style={{ textAlign: 'center', width: '70px', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>Status</th>
                                        {docTypes.map(type => (
                                            <th key={type.key} style={{ textAlign: 'center', minWidth: '60px', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>
                                                {type.label.split(' ').map((word, i) => <React.Fragment key={i}>{word}<br /></React.Fragment>)}
                                            </th>
                                        ))}
                                        <th style={{ textAlign: 'center', width: '80px', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Split<br />Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(evidenceData && evidenceData.length > 0 ? evidenceData : []).map((row, i) => (
                                        <tr key={i}>
                                            <td style={{ textAlign: 'center', position: 'sticky', left: 0, background: 'white', zIndex: 20 }}>
                                                <input type="checkbox" />
                                            </td>
                                            <td style={{ fontWeight: '500', position: 'sticky', left: '30px', background: 'white', zIndex: 20, borderRight: '1px solid #f1f5f9' }}>
                                                {row.billingDocument}
                                            </td>
                                            <td style={{ textAlign: 'center' }}>
                                                <span className="dp-icon-btn" title="View Original">📄</span>
                                                <span className="dp-icon-btn" title="Upload">📤</span>
                                            </td>
                                            <td style={{ textAlign: 'center' }}>
                                                <span className={`dp-badge ${row.evidenceStatus === '완료' ? 'dp-badge-success' : (row.evidenceStatus === '수집중' ? 'dp-badge-pending' : 'dp-badge-error')}`}>
                                                    {row.evidenceStatus || '미수집'}
                                                </span>
                                            </td>
                                            {docTypes.map(type => (
                                                <td key={type.key} style={{ textAlign: 'center' }}>
                                                    {row[type.key] === 'O' ? (
                                                        <span style={{ color: '#3b82f6', cursor: 'pointer' }}>📄</span>
                                                    ) : (
                                                        <span style={{ color: '#e2e8f0' }}>-</span>
                                                    )}
                                                </td>
                                            ))}
                                            <td style={{ textAlign: 'center' }}>
                                                <span className={`dp-badge ${row.splitStatus === 'Split 완료' ? 'dp-badge-success' : 'dp-badge-pending'}`}>
                                                    {row.splitStatus || '대기중'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                    {(!evidenceData || evidenceData.length === 0) && (
                                        <tr>
                                            <td colSpan={docTypes.length + 5} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                                                No evidence data available. Complete Step 1 to proceed.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* --- STEP 3: DATA EXTRACTION --- */}
                {activeTab === 'step3' && (
                    <div className="dp-card">
                        {/* Combined Toolbar: Filters + Actions */}
                        <div className="dp-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                            {/* Left: Filters */}
                            <div className="dp-panel-group">
                                <span className="dp-panel-label">1차 대사 결과:</span>
                                <button className="dp-filter-btn active">전체</button>
                                <button className="dp-filter-btn">✅ 일치</button>
                                <button className="dp-filter-btn">⚠️ 불일치</button>
                                <button className="dp-filter-btn">❌ 누락</button>
                            </div>

                            {/* Right: Bulk Actions & Main Buttons */}
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                <div className="dp-panel-group">
                                    <select className="dp-select-judgment" style={{ marginRight: '0.5rem', padding: '0.4rem' }}>
                                        <option value="">선택 항목 판단...</option>
                                        <option value="pass">✅ Pass</option>
                                        <option value="fail">❌ Fail</option>
                                        <option value="review">⚠️ Review</option>
                                    </select>
                                    <button className="dp-btn dp-btn-secondary">적용</button>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button className="dp-btn dp-btn-primary">⚡ 추출/비교</button>
                                    <button className="dp-btn dp-btn-secondary">💾 저장</button>
                                    <button className="dp-btn dp-btn-success">🚀 전송</button>
                                </div>
                            </div>
                        </div>

                        <div className="dp-table-wrapper">
                            <table className="dp-table dp-table-bordered">
                                <thead>
                                    {/* Group Headers */}
                                    <tr>
                                        <th rowSpan={2} style={{ width: '40px', textAlign: 'center', position: 'sticky', left: 0, zIndex: 30 }}>
                                            <input type="checkbox" />
                                        </th>
                                        <th rowSpan={2} style={{ width: '40px', textAlign: 'center', zIndex: 20 }}>Sts</th>
                                        <th rowSpan={2} style={{ width: '60px', textAlign: 'center', zIndex: 20 }}>Judg</th>
                                        <th rowSpan={2} style={{ minWidth: '120px', position: 'sticky', left: '40px', zIndex: 30 }}>Billing Doc</th>

                                        <th colSpan={4} className="dp-th-group-header">전표 데이터 (Ledger)</th>
                                        <th colSpan={4} className="dp-th-group-header">인보이스 (Invoice)</th>
                                        <th colSpan={3} className="dp-th-group-header">선하증권 (B/L)</th>
                                        <th rowSpan={2} style={{ width: '70px', textAlign: 'center' }}>Acc.</th>
                                        <th rowSpan={2} style={{ width: '80px', textAlign: 'center' }}>API Cost</th>
                                    </tr>
                                    {/* Column Headers */}
                                    <tr>
                                        {/* Step 1 */}
                                        <th className="dp-th-sub">Date</th>
                                        <th className="dp-th-sub">Amount</th>
                                        <th className="dp-th-sub">Qty</th>
                                        <th className="dp-th-sub">Incoterms</th>

                                        {/* Invoice */}
                                        <th className="dp-th-sub">Date</th>
                                        <th className="dp-th-sub">Amount</th>
                                        <th className="dp-th-sub">Qty</th>
                                        <th className="dp-th-sub">Incoterms</th>

                                        {/* BL */}
                                        <th className="dp-th-sub">Net Wgt</th>
                                        <th className="dp-th-sub">Date</th>
                                        <th className="dp-th-sub">Terms</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(() => {
                                        // Demo Data for Visual Simulation
                                        const demoData = [
                                            {
                                                billing_document: 'DEMO-MATCH-001',
                                                auto_comparison: {
                                                    status: 'match',
                                                    field_results: { date: { match: true }, amount: { match: true }, quantity: { match: true }, incoterms: { match: true } },
                                                    bl_results: { bl_net_weight: { match: true }, bl_on_board_date: { match: true }, bl_freight_terms: { match: true } }
                                                },
                                                step1_data: { date: '2024-01-01', amount: '1000.00', quantity: '100', incoterms: 'FOB' },
                                                ocr_data: { date: '2024-01-01', amount: '1000.00', quantity: '100', incoterms: 'FOB' },
                                                bl_data: { net_weight: '500kg', on_board_date: '2024-01-05', freight_payment_terms: 'Prepaid' },
                                                final_judgment: '✅',
                                                accuracy: '99.9%'
                                            },
                                            {
                                                billing_document: 'DEMO-MISMATCH-002',
                                                auto_comparison: {
                                                    status: 'mismatch',
                                                    field_results: { date: { match: false }, amount: { match: true }, quantity: { match: false }, incoterms: { match: true } },
                                                    bl_results: { bl_net_weight: { match: false }, bl_on_board_date: { match: true }, bl_freight_terms: { match: false } }
                                                },
                                                step1_data: { date: '2024-02-01', amount: '2500.00', quantity: '200', incoterms: 'CIF' },
                                                ocr_data: { date: '2024-02-02', amount: '2500.00', quantity: '190', incoterms: 'CIF' },
                                                bl_data: { net_weight: '1000kg', on_board_date: '2024-02-10', freight_payment_terms: 'Collect' },
                                                final_judgment: '⚠️',
                                                accuracy: '85.4%'
                                            }
                                        ];

                                        const displayData = [...demoData, ...(comparisonResults || [])];

                                        return displayData.map((row, i) => {
                                            const status = row.auto_comparison?.status || 'unknown';
                                            const fieldRes = row.auto_comparison?.field_results || {};
                                            const blRes = row.auto_comparison?.bl_results || {};

                                            return (
                                                <tr key={i} className={status === 'match' ? 'dp-row-match' : 'dp-row-mismatch'}>
                                                    <td style={{ textAlign: 'center', position: 'sticky', left: 0, background: 'inherit', zIndex: 10 }}>
                                                        <input type="checkbox" />
                                                    </td>
                                                    <td style={{ textAlign: 'center' }}>{status === 'match' ? '✅' : '⚠️'}</td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        <select className="dp-select-judgment" defaultValue={row.final_judgment || '-'}>
                                                            <option>-</option>
                                                            <option>✅</option>
                                                            <option>⚠️</option>
                                                            <option>❌</option>
                                                        </select>
                                                    </td>
                                                    <td style={{ fontWeight: '600', position: 'sticky', left: '40px', background: 'inherit', zIndex: 10 }}>
                                                        {row.billing_document}
                                                    </td>

                                                    {/* Step 1 */}
                                                    <td className="dp-td-group">{row.step1_data?.date || row.step1_data?.shipment_date}</td>
                                                    <td className="dp-td-group dp-text-right">{formatNumber(row.step1_data?.amount)}</td>
                                                    <td className="dp-td-group dp-text-right">{formatNumber(row.step1_data?.quantity)}</td>
                                                    <td className="dp-td-group">{row.step1_data?.incoterms}</td>

                                                    {/* Invoice */}
                                                    <td className={fieldRes.date?.match ? 'dp-cell-match' : 'dp-cell-mismatch'}>
                                                        {row.ocr_data?.date}
                                                    </td>
                                                    <td className={`${fieldRes.amount?.match ? 'dp-cell-match' : 'dp-cell-mismatch'} dp-text-right`}>
                                                        {formatNumber(row.ocr_data?.amount)}
                                                    </td>
                                                    <td className={`${fieldRes.quantity?.match ? 'dp-cell-match' : 'dp-cell-mismatch'} dp-text-right`}>
                                                        {formatNumber(row.ocr_data?.quantity)}
                                                    </td>
                                                    <td className={fieldRes.incoterms?.match ? 'dp-cell-match' : 'dp-cell-mismatch'}>
                                                        {row.ocr_data?.incoterms}
                                                    </td>

                                                    {/* BL */}
                                                    <td className={`${blRes.bl_net_weight?.match ? 'dp-cell-match' : 'dp-cell-mismatch'} dp-text-right`}>
                                                        {formatNumber(row.bl_data?.net_weight)}
                                                    </td>
                                                    <td className={blRes.bl_on_board_date?.match ? 'dp-cell-match' : 'dp-cell-mismatch'}>
                                                        {row.bl_data?.on_board_date}
                                                    </td>
                                                    <td className={blRes.bl_freight_terms?.match ? 'dp-cell-match' : 'dp-cell-mismatch'}>
                                                        {row.bl_data?.freight_payment_terms}
                                                    </td>

                                                    <td style={{ textAlign: 'center', fontWeight: '600', color: '#059669' }}>
                                                        {row.accuracy || '98.5%'}
                                                    </td>

                                                    <td style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}>
                                                        ${((row.api_usage?.input || 0) / 1000000 * 0.075).toFixed(4)}
                                                    </td>
                                                </tr>
                                            );
                                        });
                                    })()}
                                    {(!comparisonResults || comparisonResults.length === 0) && (
                                        <tr>
                                            <td colSpan={15} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                                                No extraction results available. Complete Step 2 to proceed.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* --- DASHBOARD --- */}
                {activeTab === 'dashboard' && (
                    <div className="dp-card" style={{ background: '#f8fafc', border: 'none', boxShadow: 'none' }}>
                        <div className="dp-dashboard-header">
                            <div>
                                <h1 style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.5rem' }}>📊 결과 대시보드</h1>
                                <p style={{ color: '#64748b' }}>프로젝트: {project?.name || 'IDARS PJT'}</p>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button className="dp-btn dp-btn-secondary">📥 엑셀 다운로드</button>
                                <button className="dp-btn dp-btn-secondary">🔄 새로고침</button>
                            </div>
                        </div>

                        <div className="dp-summary-bar">
                            <div className="dp-summary-item">
                                <span className="dp-summary-icon">📋</span>
                                <span className="dp-summary-label">전체 전표:</span>
                                <span className="dp-summary-value">{dashboardSummary.total}</span>
                            </div>
                            <div className="dp-summary-divider"></div>
                            <div className="dp-summary-item match">
                                <span className="dp-summary-icon">✅</span>
                                <span className="dp-summary-label">일치:</span>
                                <span className="dp-summary-value">{dashboardSummary.matched}</span>
                                <span className="dp-summary-sub">({dashboardSummary.total ? ((dashboardSummary.matched / dashboardSummary.total) * 100).toFixed(1) : 0}%)</span>
                            </div>
                            <div className="dp-summary-divider"></div>
                            <div className="dp-summary-item mismatch">
                                <span className="dp-summary-icon">⚠️</span>
                                <span className="dp-summary-label">불일치:</span>
                                <span className="dp-summary-value">{dashboardSummary.mismatched}</span>
                                <span className="dp-summary-sub">({dashboardSummary.total ? ((dashboardSummary.mismatched / dashboardSummary.total) * 100).toFixed(1) : 0}%)</span>
                            </div>
                            <div className="dp-summary-divider"></div>
                            <div className="dp-summary-item missing">
                                <span className="dp-summary-icon">❌</span>
                                <span className="dp-summary-label">확인필요:</span>
                                <span className="dp-summary-value">{dashboardSummary.missing}</span>
                                <span className="dp-summary-sub">({dashboardSummary.total ? ((dashboardSummary.missing / dashboardSummary.total) * 100).toFixed(1) : 0}%)</span>
                            </div>
                        </div>

                        <div className="dp-card" style={{ marginTop: '1.5rem' }}>
                            <div className="dp-toolbar">
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button className="dp-filter-btn active">전체 ({dashboardSummary.total})</button>
                                    <button className="dp-filter-btn">✅ 일치 ({dashboardSummary.matched})</button>
                                    <button className="dp-filter-btn">⚠️ 불일치 ({dashboardSummary.mismatched})</button>
                                    <button className="dp-filter-btn">❌ 확인필요 ({dashboardSummary.missing})</button>
                                </div>
                            </div>
                            <div className="dp-table-wrapper">
                                <table className="dp-table">
                                    <thead>
                                        <tr>
                                            <th style={{ width: '50px', textAlign: 'center' }}>No.</th>
                                            <th style={{ minWidth: '120px' }}>Billing Document</th>
                                            <th style={{ textAlign: 'center', width: '100px' }}>Status</th>
                                            <th style={{ textAlign: 'center', width: '100px' }}>Judgment</th>
                                            <th style={{ textAlign: 'center', width: '100px' }}>Match Rate</th>
                                            <th style={{ textAlign: 'center', width: '100px' }}>Issues</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(comparisonResults && comparisonResults.length > 0 ? comparisonResults : []).map((row, i) => (
                                            <tr key={i}>
                                                <td style={{ textAlign: 'center', color: '#94a3b8' }}>{i + 1}</td>
                                                <td style={{ fontWeight: '500' }}>{row.billing_document}</td>
                                                <td style={{ textAlign: 'center' }}>
                                                    <span className={`dp-badge ${row.auto_comparison?.status === 'match' ? 'dp-badge-success' : 'dp-badge-error'}`}>
                                                        {row.auto_comparison?.status === 'match' ? 'MATCH' : 'FAIL'}
                                                    </span>
                                                </td>
                                                <td style={{ textAlign: 'center' }}>
                                                    {row.final_judgment === '✅' ? <span className="text-green">PASS</span> :
                                                        row.final_judgment === '❌' ? <span className="text-red">FAIL</span> : '-'}
                                                </td>
                                                <td style={{ textAlign: 'center' }}>
                                                    {row.auto_comparison?.status === 'match' ? '100%' : '85%'}
                                                </td>
                                                <td style={{ textAlign: 'center' }}>
                                                    {row.auto_comparison?.status === 'mismatch' ? <span style={{ color: '#ef4444' }}>2 Fields</span> : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                        {(!comparisonResults || comparisonResults.length === 0) && (
                                            <tr>
                                                <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                                                    No dashboard data available.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DesignPreview;
