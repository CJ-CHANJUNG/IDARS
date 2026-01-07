import React, { useState, useEffect } from 'react';
import './Step3DtermDataExtraction.css'; // Dedicated D-Term styles


const Step3DtermDataExtraction = ({ projectId, onNext, onBack }) => {
    const [extractionResults, setExtractionResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState({ current: 0, total: 0, message: '' });
    const [error, setError] = useState(null);
    const [hasExtracted, setHasExtracted] = useState(false);

    // Selection State
    const [selectedItems, setSelectedItems] = useState(new Set());
    // Detail View State
    const [showDetails, setShowDetails] = useState(false);

    // State for Viewer
    const [viewerState, setViewerState] = useState({ isOpen: false, files: [], title: '' });

    // Selection Handlers
    const handleSelectAll = (e) => {
        if (e.target.checked) {
            const allIds = new Set(extractionResults.map(r => r.billing_document));
            setSelectedItems(allIds);
        } else {
            setSelectedItems(new Set());
        }
    };

    const handleSelectItem = (id) => {
        const newSet = new Set(selectedItems);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        setSelectedItems(newSet);
    };

    const isAllSelected = extractionResults.length > 0 && extractionResults.every(r => selectedItems.has(r.billing_document));

    // Initial Load - Check for existing results
    useEffect(() => {
        fetchResults();
    }, [projectId]);

    const fetchResults = async () => {
        try {
            const response = await fetch(`http://localhost:5000/api/projects/${projectId}/step3/dterm/results`);
            if (response.ok) {
                const data = await response.json();
                if (data.results && data.results.length > 0) {
                    setExtractionResults(data.results);
                    // Check if actually extracted (not just pending list)
                    const isProcessed = data.results.some(r => r.status && r.status !== 'pending');
                    setHasExtracted(isProcessed);
                }
            }
        } catch (err) {
            console.error("Failed to load existing results:", err);
        }
    };

    const handleStartExtraction = async () => {
        setLoading(true);
        setError(null);
        setProgress({ current: 0, total: 0, message: 'Starting extraction...' });

        try {
            // Polling for progress
            const progressInterval = setInterval(async () => {
                try {
                    const res = await fetch('http://localhost:5000/api/extraction/progress');
                    const data = await res.json();
                    if (data[projectId]) {
                        const p = data[projectId];
                        setProgress({
                            current: p.current,
                            total: p.total,
                            message: p.message
                        });
                    }
                } catch (e) {
                    console.error("Progress fetch error:", e);
                }
            }, 1000);

            // Determine target IDs
            const targetIds = selectedItems.size > 0 ? Array.from(selectedItems) : null;

            const response = await fetch(`http://localhost:5000/api/projects/${projectId}/step3/dterm/extract`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_ids: targetIds }) // Process selected or all
            });

            clearInterval(progressInterval);

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Extraction failed');
            }

            // Reload full results to include both Extracted and Pending items
            await fetchResults();
            setHasExtracted(true);

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleViewFile = async (item) => {
        let filesToView = [];
        let title = '';

        // 1. Direct File (Robust Path)
        if (item.file_path) {
            filesToView = [{
                filename: item.file_name,
                url: `/api/projects/${projectId}/files/${item.file_path}`,
                type: 'dterm'
            }];
            title = `증빙: ${item.file_name}`;
        }
        // 2. Legacy File Name Logic
        else if (item.file_name && item.file_name !== '-' && item.file_name !== 'Unknown') {
            const encodedFilename = encodeURIComponent(item.file_name);
            filesToView = [{
                filename: item.file_name,
                url: `/api/projects/${projectId}/files/step2_evidence_collection/dterm_downloads/${encodedFilename}`,
                type: 'dterm'
            }];
            title = `증빙: ${item.file_name}`;
        }
        // 3. Fallback Search
        else if (item.billing_document) {
            try {
                const res = await fetch(`/api/projects/${projectId}/evidence/search?billingDocument=${item.billing_document}`);
                const files = await res.json();
                if (files && files.length > 0) {
                    filesToView = files.map(f => ({
                        ...f,
                        url: `/api/projects/${projectId}/files/${f.path}`
                    }));
                    title = `증빙: ${item.billing_document}`;
                } else {
                    alert('해당 전표의 증빙 파일을 찾을 수 없습니다.');
                    return;
                }
            } catch (e) {
                console.error(e);
                alert('파일 열기 실패');
                return;
            }
        } else {
            return;
        }

        // Open in New Window (Pop-out)
        if (filesToView.length > 0) {
            const viewerData = {
                files: filesToView,
                title: title,
                timestamp: Date.now()
            };
            localStorage.setItem('pdfViewerPopoutState', JSON.stringify(viewerData));
            window.open('/?mode=viewer', '_blank', 'width=1400,height=900');
        }
    };

    // Helper for Diff Badge
    const renderDiffBadge = (diffDays) => {
        if (diffDays === null || diffDays === undefined) return <span className="status-badge pending">-</span>;

        let badgeClass = 'success';
        if (Math.abs(diffDays) > 3) badgeClass = 'danger';
        else if (diffDays !== 0) badgeClass = 'warning';

        const sign = diffDays > 0 ? '+' : '';
        return <span className={`status-badge ${badgeClass}`}>{sign}{diffDays} Days</span>;
    };

    return (
        <div className="step-container">
            <h2 className="step-title">Step 3: 증빙 도착일 검증 (D-Term)</h2>
            <p className="step-description">
                AI가 추출한 화물 도착일(ATA)과 SAP 상의 ATA/매출일을 비교합니다.
            </p>

            {/* Actions Area */}
            <div className="action-bar">
                {!hasExtracted || loading ? (
                    <button
                        className="btn-primary"
                        onClick={handleStartExtraction}
                        disabled={loading}
                        style={{ padding: '0.6rem 1.2rem', fontSize: '1rem' }}
                    >
                        {loading ? 'AI 분석 진행 중...' : '▶ 증빙대사 시작 (AI Analysis)'}
                    </button>
                ) : (
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <span style={{ alignSelf: 'center', color: '#059669', fontWeight: '600' }}>✓ 분석 완료</span>
                        <button
                            className="btn-secondary"
                            onClick={handleStartExtraction}
                            style={{ padding: '0.4rem 1rem', fontSize: '0.9rem' }}
                        >
                            🔄 증빙대사 실행
                        </button>
                    </div>
                )}
            </div>

            {/* Error Message */}
            {error && <div className="error-message">{error}</div>}

            {/* Progress Bar */}
            {loading && (
                <div className="progress-container">
                    <div className="progress-bar-wrapper">
                        <div
                            className="progress-bar-fill"
                            style={{ width: `${(progress.current / Math.max(progress.total, 1)) * 100}%` }}
                        ></div>
                    </div>
                    <div className="progress-text">
                        {progress.message} ({progress.current}/{progress.total})
                    </div>
                </div>
            )}

            {/* Results Table */}
            {!loading && extractionResults.length > 0 && (
                <div className="table-container">
                    <table className="comparison-table">
                        <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: '#f8f9fa' }}>
                            {/* Header Row 1: Groups */}
                            <tr>
                                <th rowSpan="2" style={{ width: '40px', textAlign: 'center', borderRight: '1px solid #e5e7eb' }}>
                                    <input
                                        type="checkbox"
                                        checked={isAllSelected}
                                        onChange={handleSelectAll}
                                        style={{ cursor: 'pointer' }}
                                    />
                                </th>
                                <th
                                    colSpan={showDetails ? 13 : 7}
                                    style={{ textAlign: 'center', borderBottom: '1px solid #e5e7eb', backgroundColor: '#f3f4f6', color: '#4b5563', cursor: 'pointer', userSelect: 'none' }}
                                    onClick={() => setShowDetails(!showDetails)}
                                    title="클릭하여 상세 정보 펼치기/접기"
                                >
                                    전표 데이터 (Slip Data)
                                    <span style={{ marginLeft: '8px', fontSize: '0.8rem', color: '#6b7280' }}>
                                        {showDetails ? '[-] 접기' : '[+] 더보기'}
                                    </span>
                                </th>
                                <th colSpan="3" style={{ textAlign: 'center', borderBottom: '1px solid #e5e7eb', backgroundColor: '#eff6ff', color: '#1e3a8a' }}>
                                    AI 분석 결과 (AI Analysis Result)
                                </th>
                                <th colSpan="2" style={{ textAlign: 'center', borderBottom: '1px solid #e5e7eb' }}>
                                    검증 (Verification)
                                </th>
                            </tr>
                            {/* Header Row 2: Details */}
                            <tr>
                                {/* Slip Data Columns */}
                                <th style={{ minWidth: '100px' }}>전표번호</th>
                                <th style={{ minWidth: '90px' }}>SAP ATA</th>
                                <th style={{ minWidth: '90px' }}>SAP ETA</th>
                                <th style={{ minWidth: '90px' }}>매출일</th>
                                <th style={{ minWidth: '60px' }}>Curr</th>
                                <th style={{ minWidth: '100px' }}>매출액</th>
                                <th style={{ minWidth: '100px' }}>매출액(Loc)</th>
                                {showDetails && (
                                    <>
                                        <th style={{ minWidth: '80px' }}>TC</th>
                                        <th style={{ minWidth: '80px' }}>SO</th>
                                        <th style={{ minWidth: '120px' }}>Customer</th>
                                        <th style={{ minWidth: '80px' }}>Invoice</th>
                                        <th style={{ minWidth: '80px' }}>Group</th>
                                        <th style={{ minWidth: '80px' }}>Sales</th>
                                    </>
                                )}

                                {/* AI Columns */}
                                <th className="highlight-col" style={{ minWidth: '100px' }}>증빙 도착일(AI)</th>
                                <th style={{ minWidth: '100px' }}>문서 유형</th>
                                <th style={{ minWidth: '200px' }}>근거(Evidence)</th>

                                {/* Verification Columns */}
                                <th style={{ minWidth: '100px' }}>상태(Status)</th>
                                <th style={{ minWidth: '80px' }}>Diff</th>
                            </tr>
                        </thead>
                        <tbody>
                            {extractionResults.map((item, idx) => (
                                <tr key={idx} style={{ backgroundColor: selectedItems.has(item.billing_document) ? '#f0f9ff' : 'transparent', whiteSpace: 'nowrap' }}>
                                    <td style={{ textAlign: 'center' }}>
                                        <input
                                            type="checkbox"
                                            checked={selectedItems.has(item.billing_document)}
                                            onChange={() => handleSelectItem(item.billing_document)}
                                            style={{ cursor: 'pointer' }}
                                        />
                                    </td>

                                    {/* Step 1 Columns */}
                                    <td style={{ fontWeight: '600' }}>{item.billing_document}</td>
                                    <td>{item.sap_ata_date || '-'}</td>
                                    <td style={{ color: '#6b7280' }}>{item.sap_eta_date || '-'}</td>
                                    <td style={{ color: '#6b7280' }}>{item.sap_billing_date || '-'}</td>

                                    {/* Amount Details */}
                                    <td style={{ textAlign: 'center', color: '#4b5563' }}>{item.sap_curr || '-'}</td>
                                    <td style={{ textAlign: 'right', fontWeight: '500' }}>
                                        {item.sap_amount ? Number(String(item.sap_amount).replace(/,/g, '')).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                                    </td>
                                    <td style={{ textAlign: 'right', color: '#6b7280' }}>
                                        {item.sap_amount_loc ? Number(String(item.sap_amount_loc).replace(/,/g, '')).toLocaleString() : '-'}
                                    </td>

                                    {showDetails && (
                                        <>
                                            <td>{item.tc ? String(item.tc).replace(/\.0$/, '') : '-'}</td>
                                            <td>{item.so || '-'}</td>
                                            <td title={item.customer_desc} style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {item.customer_desc || '-'}
                                            </td>
                                            <td>{item.invoice || '-'}</td>
                                            <td>{item.group || '-'}</td>
                                            <td>{item.sales_person || '-'}</td>
                                        </>
                                    )}

                                    {/* AI Columns */}
                                    <td className="highlight-date" style={{ fontWeight: 'bold', color: '#1d4ed8' }}>
                                        {item.arrival_date || '-'}
                                        {item.date_confidence > 0 && (
                                            <span
                                                className={`confidence-badge ${item.date_confidence > 0.8 ? 'confidence-high' : 'confidence-check'}`}
                                                style={{ marginLeft: '6px', fontSize: '0.65rem', verticalAlign: 'middle' }}
                                            >
                                                {item.date_confidence > 0.8 ? 'High' : 'Check'}
                                            </span>
                                        )}
                                    </td>
                                    <td>{item.document_type || 'Unknown'}</td>
                                    <td className="reasoning-cell" title={item.evidence_text || item.reasoning}>
                                        <div style={{
                                            maxWidth: '200px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            fontSize: '0.75rem',
                                            color: '#4b5563',
                                            cursor: 'help'
                                        }}>
                                            {item.evidence_text ? `"${item.evidence_text}"` : (item.reasoning || '-')}
                                        </div>
                                    </td>
                                    <td>
                                        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                                            {/* Verification Status */}
                                            {(item.verification_status && item.verification_status !== 'Unidentified') ? (
                                                <span className={`status-badge ${item.verification_status.includes('Perfect') ? 'success' :
                                                    item.verification_status.includes('Match') ? 'info' : 'warning'
                                                    }`}>
                                                    {item.verification_status === 'Perfect Match' ? 'Perfect' :
                                                        item.verification_status === 'Match - Date Only' ? 'DateOnly' :
                                                            item.verification_status}
                                                </span>
                                            ) : (
                                                <span className="status-badge pending">{item.status || 'Pending'}</span>
                                            )}

                                            {/* File View Icon */}
                                            {item.file_name && (
                                                <span
                                                    onClick={() => handleViewFile(item)}
                                                    style={{ cursor: 'pointer', fontSize: '1rem', marginLeft: '4px', display: 'flex', alignItems: 'center' }}
                                                    title={`View ${item.file_name}`}
                                                >
                                                    📄
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {renderDiffBadge(item.diff_days)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {!loading && extractionResults.length === 0 && !error && (
                <div className="empty-state">
                    검증 결과가 없습니다. '도착 증빙 검증 시작' 버튼을 눌러주세요.
                </div>
            )}

            {/* Bottom Actions */}
            <div className="bottom-actions">
                <button className="btn-secondary" onClick={onBack}>이전 단계</button>
                <button className="btn-primary" onClick={onNext} disabled={loading}>
                    다음 단계 (대시보드)
                </button>
            </div>
            {/* PDF Viewer Modal */}

        </div>
    );
};

export default Step3DtermDataExtraction;
