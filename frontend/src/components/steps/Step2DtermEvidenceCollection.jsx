import React, { useState, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import EvidenceUploadModal from '../EvidenceUploadModal';
import ProgressBar from '../ProgressBar';
import '../DesignPreview.css';

const Step2DtermEvidenceCollection = () => {
    const {
        project,
        evidenceData, setEvidenceData,
        isLoading, setIsLoading,
        setSidebarView,
        loadProjectData
    } = useProject();

    // Local State
    const [selectedRows, setSelectedRows] = useState(new Set());
    const [showDownloadProgress, setShowDownloadProgress] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState({ current: 0, total: 0, message: '', status: '' });
    const [uploadModalState, setUploadModalState] = useState({ isOpen: false, billingDocument: '' });

    // --- Effects ---
    useEffect(() => {
        if (project) {
            checkEvidenceStatus();
        }
    }, [project]);

    // --- Selection Handlers ---
    const handleSelectAll = (e) => {
        if (e.target.checked) {
            const allIds = new Set(evidenceData.map(row => row['Billing No.'] || row.billingDocument));
            setSelectedRows(allIds);
        } else {
            setSelectedRows(new Set());
        }
    };

    const handleSelectRow = (billingDoc) => {
        const newSelected = new Set(selectedRows);
        if (newSelected.has(billingDoc)) {
            newSelected.delete(billingDoc);
        } else {
            newSelected.add(billingDoc);
        }
        setSelectedRows(newSelected);
    };

    // --- Action Handlers ---
    const checkEvidenceStatus = async () => {
        if (!project) return;
        try {
            const response = await fetch(`/api/projects/${project.id}/evidence/status`);
            const statusMap = await response.json();

            if (response.ok) {
                setEvidenceData(prevData => {
                    return prevData.map(row => {
                        const billingDoc = row['Billing No.'] || row.billingDocument;
                        const docStatus = statusMap[billingDoc];
                        if (docStatus) {
                            const newRow = { ...row };
                            // Update status based on whether files exist
                            if (docStatus.original || docStatus.files_count > 0) {
                                newRow.evidenceStatus = '완료';
                                newRow.fileCount = docStatus.files_count || 0;
                            } else {
                                newRow.evidenceStatus = '미수집';
                                newRow.fileCount = 0;
                            }
                            return newRow;
                        }
                        return { ...row, evidenceStatus: '미수집', fileCount: 0 };
                    });
                });
            }
        } catch (err) {
            console.error("Error checking evidence status:", err);
        }
    };

    const handleDtermSAPDownload = async () => {
        if (!project) return;

        const targetDocuments = selectedRows.size > 0 ? Array.from(selectedRows) : null;
        const message = targetDocuments
            ? `선택된 ${targetDocuments.length}개 전표의 D조건 증빙을 SAP에서 다운로드 하시겠습니까?`
            : '전체 전표의 D조건 증빙을 SAP에서 다운로드 하시겠습니까?';

        if (!window.confirm(message)) return;

        const forceRedownload = window.confirm(
            '이미 다운로드된 파일이 있을 경우:\n\n' +
            '「확인」 = 다시 다운로드 (최신 파일 보장)\n' +
            '「취소」 = 건너뛰기 (빠른 실행)'
        );

        setIsLoading(true);
        try {
            const requestBody = { targetDocuments, forceRedownload };
            const response = await fetch(`/api/projects/${project.id}/dterm-sap-download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            const result = await response.json();

            if (response.ok) {
                pollDtermProgress();
                setSelectedRows(new Set());
            } else {
                alert('SAP 다운로드 실패: ' + result.error);
                setIsLoading(false);
            }
        } catch (err) {
            console.error(err);
            alert('SAP 다운로드 시작 중 오류 발생: ' + err.message);
            setIsLoading(false);
        }
    };

    const pollDtermProgress = () => {
        if (!project) return;
        setShowDownloadProgress(true);
        setDownloadProgress({ current: 0, total: 0, message: 'SAP 연결 중...', status: 'running' });

        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/dterm/progress/${project.id}`);
                if (response.ok) {
                    const progress = await response.json();
                    setDownloadProgress({
                        current: progress.current || 0,
                        total: progress.total || 0,
                        message: progress.message || '',
                        status: progress.status || 'running'
                    });

                    if (progress.status === 'completed' || progress.status === 'error') {
                        clearInterval(pollInterval);
                        setIsLoading(false);
                        setTimeout(() => setShowDownloadProgress(false), 3000);

                        if (progress.status === 'completed') {
                            checkEvidenceStatus();
                            alert('✅ D조건 증빙 다운로드 완료!');
                        } else {
                            alert('❌ 다운로드 오류: ' + progress.message);
                        }
                    }
                }
            } catch (err) {
                console.error('Progress polling error:', err);
            }
        }, 1000);
    };

    const handleConfirmStep2 = async () => {
        if (!project) return;
        if (!evidenceData || evidenceData.length === 0) {
            alert('증빙 데이터가 없습니다.');
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${project.id}/confirm-step2`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ evidenceData: evidenceData })
            });
            const result = await response.json();

            if (response.ok) {
                setSidebarView('step3');
                alert('✅ D조건 증빙이 성공적으로 확정되었습니다!\n\nStep 3 (데이터 추출 및 대사)로 이동합니다.');
                loadProjectData(project.id);
            } else {
                alert('확정 실패: ' + result.error);
            }
        } catch (err) {
            console.error('[CONFIRM STEP2] Error:', err);
            alert('확정 중 오류 발생: ' + err.message);
        }
        setIsLoading(false);
    };

    const handleUnconfirm = async () => {
        if (!project) return;
        if (!window.confirm(`Step 2 확정을 취소하시겠습니까?\n이후 단계의 데이터가 잠금 해제되거나 영향을 받을 수 있습니다.`)) return;

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${project.id}/unconfirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step: 2 })
            });
            const result = await response.json();

            if (response.ok) {
                alert(`✅ Step 2 확정이 취소되었습니다.`);
                await loadProjectData(project.id);
            } else {
                alert('확정 취소 실패: ' + result.error);
            }
        } catch (err) {
            console.error('[UNCONFIRM] Error:', err);
            alert('확정 취소 중 오류 발생: ' + err.message);
        }
        setIsLoading(false);
    };

    const handleViewEvidence = async (row) => {
        const billingDoc = row['Billing No.'] || row.billingDocument;
        try {
            const response = await fetch(`/api/projects/${project.id}/evidence/search?billingDocument=${billingDoc}`);
            let files = await response.json();

            if (files && files.length > 0) {
                const filesWithUrl = files.map(f => ({
                    ...f,
                    url: `/api/projects/${project.id}/files/${f.path}`
                }));

                // 새 창으로 증빙 뷰어 열기
                const viewerData = {
                    files: filesWithUrl,
                    title: `D조건 증빙: ${billingDoc}`,
                    timestamp: Date.now()
                };

                localStorage.setItem('pdfViewerPopoutState', JSON.stringify(viewerData));
                window.open('/?mode=viewer', '_blank', 'width=1400,height=900');
            } else {
                alert('해당 전표의 증빙 파일을 찾을 수 없습니다.');
            }
        } catch (err) {
            console.error(err);
            alert('증빙 파일을 검색하는데 실패했습니다.');
        }
    };

    const handleUploadEvidence = (row) => {
        const billingDoc = row['Billing No.'] || row.billingDocument;
        setUploadModalState({
            isOpen: true,
            billingDocument: billingDoc
        });
    };

    const onManualUpload = async (file, billingDocument) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('billingDocument', billingDocument);

        try {
            const response = await fetch(`/api/projects/${project.id}/evidence/upload`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                alert('업로드 성공!');
                checkEvidenceStatus();
            } else {
                alert('업로드 실패: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('파일 업로드 중 오류 발생');
        }
    };

    return (
        <div className="dp-card">
            {showDownloadProgress && (
                <ProgressBar
                    current={downloadProgress.current}
                    total={downloadProgress.total}
                    message={downloadProgress.message}
                    status={downloadProgress.status}
                />
            )}
            <div className="dp-dashboard-header" style={{ padding: '1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.5rem' }}>📦 Step 2: D조건 증빙 수집</h1>
                    <p style={{ color: '#64748b' }}>D조건 전표의 도착 증빙을 수집하고 관리합니다 (이메일, 이미지, PDF 등)</p>
                </div>
                <div className="dp-panel-controls" style={{ border: 'none', padding: 0, background: 'transparent' }}>
                    <div className="dp-panel-group">
                        <button
                            className="dp-btn"
                            onClick={() => loadProjectData(project.id)}
                            disabled={isLoading}
                            title="Step1에서 데이터를 재확정한 경우 클릭하여 새로고침"
                        >
                            🔄 데이터 새로고침
                        </button>
                        <button
                            className="dp-btn dp-btn-primary"
                            onClick={handleDtermSAPDownload}
                            disabled={isLoading}
                        >
                            📥 SAP 증빙 다운로드 (ZTDR0210)
                        </button>
                        <button
                            className={`dp-btn ${project?.steps?.step2?.status === 'completed' ? 'dp-btn-danger' : 'dp-btn-success'}`}
                            onClick={project?.steps?.step2?.status === 'completed' ? handleUnconfirm : handleConfirmStep2}
                            disabled={isLoading || (project?.steps?.step3?.status === 'completed')}
                            style={{ opacity: (project?.steps?.step3?.status === 'completed') ? 0.5 : 1 }}
                        >
                            {project?.steps?.step2?.status === 'completed' ? '↩️ 확정 취소' : '✅ 증빙 확정'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="dp-summary-bar" style={{ margin: '1.5rem', width: 'auto' }}>
                <div className="dp-summary-item">
                    <span className="dp-summary-label">전체:</span>
                    <span className="dp-summary-value">{evidenceData.length}</span>
                </div>
                <div className="dp-summary-divider"></div>
                <div className="dp-summary-item pending">
                    <span className="dp-summary-label">미수집:</span>
                    <span className="dp-summary-value" style={{ color: '#d97706' }}>
                        {evidenceData.filter(r => r.evidenceStatus === '미수집').length}
                    </span>
                </div>
                <div className="dp-summary-divider"></div>
                <div className="dp-summary-item match">
                    <span className="dp-summary-label">수집완료:</span>
                    <span className="dp-summary-value">
                        {evidenceData.filter(r => r.evidenceStatus === '완료').length}
                    </span>
                </div>
            </div>

            {evidenceData.length > 0 ? (
                <div className="dp-table-wrapper">
                    <table className="dp-table dp-table-bordered">
                        <thead>
                            <tr>
                                <th style={{ width: '30px', position: 'sticky', left: 0, zIndex: 30, background: '#f8fafc' }}>
                                    <input
                                        type="checkbox"
                                        checked={evidenceData.length > 0 && selectedRows.size === evidenceData.length}
                                        onChange={handleSelectAll}
                                        style={{ cursor: 'pointer' }}
                                    />
                                </th>
                                <th style={{ minWidth: '140px', textAlign: 'left', position: 'sticky', left: '30px', zIndex: 30, background: '#f8fafc', borderRight: '1px solid #e2e8f0', fontSize: '0.8rem' }}>전표번호</th>
                                <th style={{ minWidth: '120px', textAlign: 'left', fontSize: '0.8rem' }}>매출인식일</th>
                                <th style={{ minWidth: '120px', textAlign: 'left', fontSize: '0.8rem' }}>ATA Date</th>
                                <th style={{ minWidth: '120px', textAlign: 'left', fontSize: '0.8rem' }}>ETA Date</th>
                                <th style={{ minWidth: '150px', textAlign: 'left', fontSize: '0.8rem' }}>거래처</th>
                                <th style={{ minWidth: '100px', textAlign: 'left', fontSize: '0.8rem' }}>Incoterms</th>
                                <th style={{ width: '80px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>증빙</th>
                                <th style={{ width: '100px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>수집상태</th>
                                <th style={{ width: '80px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>파일수</th>
                            </tr>
                        </thead>
                        <tbody>
                            {evidenceData.map((row, index) => {
                                const billingDoc = row['Billing No.'] || row.billingDocument;
                                // 고유 키 생성: billingDoc + index (중복 전표번호 대응)
                                const uniqueKey = `${billingDoc || 'unknown'}_${index}`;
                                return (
                                    <tr key={uniqueKey}>
                                        <td style={{ textAlign: 'center', position: 'sticky', left: 0, background: 'white', zIndex: 20 }}>
                                            <input
                                                type="checkbox"
                                                checked={selectedRows.has(billingDoc)}
                                                onChange={() => handleSelectRow(billingDoc)}
                                                style={{ cursor: 'pointer' }}
                                            />
                                        </td>
                                        <td style={{ fontWeight: '500', position: 'sticky', left: '30px', background: 'white', zIndex: 20, borderRight: '1px solid #f1f5f9' }}>
                                            {billingDoc}
                                        </td>
                                        <td>{row.billingDate || '-'}</td>
                                        <td>{row.ata || '-'}</td>
                                        <td>{row.eta || '-'}</td>
                                        <td>{row.customer || '-'}</td>
                                        <td>{row.incoterms || '-'}</td>
                                        <td style={{ textAlign: 'center' }}>
                                            <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                                                <span
                                                    className="dp-icon-btn"
                                                    onClick={() => handleViewEvidence(row)}
                                                    title="증빙 보기"
                                                    style={{ opacity: row.evidenceStatus === '미수집' ? 0.3 : 1, cursor: row.evidenceStatus === '미수집' ? 'not-allowed' : 'pointer' }}
                                                >
                                                    📄
                                                </span>
                                                <span
                                                    className="dp-icon-btn"
                                                    onClick={() => handleUploadEvidence(row)}
                                                    title="수동 업로드"
                                                >
                                                    📤
                                                </span>
                                            </div>
                                        </td>
                                        <td style={{ textAlign: 'center' }}>
                                            <span className={`dp-badge ${row.evidenceStatus === '완료' ? 'dp-badge-success' : 'dp-badge-error'}`}>
                                                {row.evidenceStatus || '미수집'}
                                            </span>
                                        </td>
                                        <td style={{ textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                                            {row.fileCount || 0}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
                    <p>증빙 데이터가 없습니다.</p>
                    <p>먼저 Step 1에서 D조건 전표를 확정해주세요.</p>
                </div>
            )}

            <EvidenceUploadModal
                isOpen={uploadModalState.isOpen}
                onClose={() => setUploadModalState({ isOpen: false, billingDocument: '' })}
                onUpload={onManualUpload}
                billingDocument={uploadModalState.billingDocument}
            />
        </div>
    );
};

export default Step2DtermEvidenceCollection;
