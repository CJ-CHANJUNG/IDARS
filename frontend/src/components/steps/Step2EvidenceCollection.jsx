import React, { useState, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import DataImportModal from '../DataImportModal';
import PDFViewerModal from '../PDFViewerModal';
import EvidenceUploadModal from '../EvidenceUploadModal';
import ProgressBar from '../ProgressBar';
import '../DesignPreview.css';

const Step2EvidenceCollection = () => {
    const {
        project,
        evidenceData, setEvidenceData,
        isLoading, setIsLoading,
        setSidebarView,
        loadProjectData
    } = useProject();

    // Local State
    const [selectedRows, setSelectedRows] = useState(new Set());
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const [importModalTab, setImportModalTab] = useState('dms');
    const [showDownloadProgress, setShowDownloadProgress] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState({ current: 0, total: 0, message: '', status: '' });

    const [pdfViewerState, setPdfViewerState] = useState({
        isOpen: false,
        files: [],
        title: '',
        billingDocument: null
    });

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
            const allIds = new Set(evidenceData.map(row => row.billingDocument));
            setSelectedRows(allIds);
        } else {
            setSelectedRows(new Set());
        }
    };

    const handleSelectRow = (billingDocument) => {
        const newSelected = new Set(selectedRows);
        if (newSelected.has(billingDocument)) {
            newSelected.delete(billingDocument);
        } else {
            newSelected.add(billingDocument);
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
                        const docStatus = statusMap[row.billingDocument];
                        if (docStatus) {
                            const newRow = { ...row };
                            // Update overall status
                            if (docStatus.original || docStatus.split) {
                                newRow.evidenceStatus = '완료';
                            }
                            // Update Split Status
                            newRow.splitStatus = docStatus.split ? 'Split 완료' : '대기중';

                            // Update Document Type Columns
                            newRow.Bill_of_Lading = '';
                            newRow.Commercial_Invoice = '';
                            newRow.Packing_List = '';
                            newRow.Weight_List = '';
                            newRow.Mill_Certificate = '';
                            newRow.Cargo_Insurance = '';
                            newRow.Certificate_Origin = '';
                            newRow.Customs_clearance_Letter = '';
                            newRow.Delivery_Note = '';
                            newRow.Other = '';

                            if (docStatus.types && docStatus.types.length > 0) {
                                if (docStatus.types.includes('Bill_of_Lading')) newRow.Bill_of_Lading = 'O';
                                if (docStatus.types.includes('Commercial_Invoice')) newRow.Commercial_Invoice = 'O';
                                if (docStatus.types.includes('Packing_List')) newRow.Packing_List = 'O';
                                if (docStatus.types.includes('Weight_List')) newRow.Weight_List = 'O';
                                if (docStatus.types.includes('Mill_Certificate')) newRow.Mill_Certificate = 'O';
                                if (docStatus.types.includes('Cargo_Insurance')) newRow.Cargo_Insurance = 'O';
                                if (docStatus.types.includes('Certificate_Origin')) newRow.Certificate_Origin = 'O';
                                if (docStatus.types.includes('Customs_clearance_Letter')) newRow.Customs_clearance_Letter = 'O';
                                if (docStatus.types.includes('Delivery_Note')) newRow.Delivery_Note = 'O';
                                if (docStatus.types.includes('Other')) newRow.Other = 'O';
                            }
                            return newRow;
                        }
                        return row;
                    });
                });
            }
        } catch (err) {
            console.error("Error checking evidence status:", err);
        }
    };

    const handleDMSDownload = async () => {
        if (!project) return;

        const targetDocuments = selectedRows.size > 0 ? Array.from(selectedRows) : null;
        const message = targetDocuments
            ? `선택된 ${targetDocuments.length}개 전표의 증빙을 다운로드 하시겠습니까?`
            : '전체 전표의 증빙을 다운로드 하시겠습니까?';

        if (!window.confirm(message)) return;

        const forceRedownload = window.confirm(
            '이미 다운로드된 파일이 있을 경우:\n\n' +
            '「확인」 = 다시 다운로드 (최신 파일 보장)\n' +
            '「취소」 = 건너뛰기 (빠른 실행)'
        );

        setIsLoading(true);
        try {
            const requestBody = { targetDocuments, forceRedownload };
            const response = await fetch(`/api/projects/${project.id}/dms-download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            const result = await response.json();

            if (response.ok) {
                // 진행률 바가 바로 표시되므로 alert 불필요
                pollDMSProgress();
                setSelectedRows(new Set());
            } else {
                alert('DMS Download failed: ' + result.error);
                setIsLoading(false);
            }
        } catch (err) {
            console.error(err);
            alert('Error starting DMS download: ' + err.message);
            setIsLoading(false);
        }
    };

    const pollDMSProgress = () => {
        if (!project) return;
        setShowDownloadProgress(true);
        setDownloadProgress({ current: 0, total: 0, message: 'Starting...', status: 'running' });

        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/dms/progress/${project.id}`);
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
                            alert('✅ DMS 다운로드 완료!');
                        } else {
                            alert('❌ Download Error: ' + progress.message);
                        }
                    }
                }
            } catch (err) {
                console.error('Progress polling error:', err);
            }
        }, 1000);
    };

    const handleSplitEvidence = async () => {
        if (!project) return;
        const targetDocuments = selectedRows.size > 0 ? Array.from(selectedRows) : null;
        const message = targetDocuments
            ? `선택된 ${targetDocuments.length}개 전표의 증빙을 Split 하시겠습니까?`
            : '전체 증빙 문서를 Split 하시겠습니까?';

        if (!window.confirm(message)) return;

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${project.id}/split-evidence`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ targetDocuments })
            });
            const result = await response.json();

            if (response.ok) {
                // 진행률 바가 바로 표시되므로 alert 불필요
                pollSplitProgress();
                setSelectedRows(new Set());
            } else {
                alert('Split failed: ' + result.error);
                setIsLoading(false);
            }
        } catch (err) {
            console.error(err);
            alert('Error starting split: ' + err.message);
            setIsLoading(false);
        }
    };

    const pollSplitProgress = () => {
        if (!project) return;
        setShowDownloadProgress(true);
        setDownloadProgress({ current: 0, total: 0, message: 'Split 준비 중...', status: 'running' });

        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/split/progress/${project.id}`);
                if (response.ok) {
                    const progress = await response.json();
                    setDownloadProgress({
                        current: progress.current || 0,
                        total: progress.total || 0,
                        message: progress.message || 'Processing...', status: progress.status || 'running'
                    });

                    if (progress.status === 'completed' || progress.status === 'error') {
                        clearInterval(pollInterval);
                        setIsLoading(false);
                        setTimeout(() => setShowDownloadProgress(false), 3000);

                        if (progress.status === 'completed') {
                            checkEvidenceStatus();
                            alert('✅ PDF Split 완료!');
                        } else {
                            alert('❌ Split Error: ' + progress.message);
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
                alert('✅ 증빙이 성공적으로 확정되었습니다!\n\nStep 3 (데이터 추출)로 이동합니다.');
                loadProjectData(project.id);
            } else {
                alert('Failed to confirm Step 2: ' + result.error);
            }
        } catch (err) {
            console.error('[CONFIRM STEP2] Error:', err);
            alert('Error confirming Step 2: ' + err.message);
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
                alert('Failed to unconfirm: ' + result.error);
            }
        } catch (err) {
            console.error('[UNCONFIRM] Error:', err);
            alert('Error unconfirming step: ' + err.message);
        }
        setIsLoading(false);
    };

    const handleViewEvidence = async (row, filterType = null) => {
        try {
            const response = await fetch(`/api/projects/${project.id}/evidence/search?billingDocument=${row.billingDocument}`);
            let files = await response.json();

            if (files && files.length > 0) {
                // filterType 여부에 따라 다르게 처리
                if (filterType) {
                    // 오른쪽 컬럼 (BL, Invoice 등) 클릭 → split 파일만 표시
                    files = files.filter(f => f.type === 'split');

                    // 문서 타입별 필터링
                    const filtered = files.filter(f => {
                        const lowerName = f.filename.toLowerCase();
                        if (filterType === 'Bill_of_Lading') return lowerName.includes('bill_of_lading') || lowerName.includes('b_l');
                        if (filterType === 'Commercial_Invoice') return lowerName.includes('commercial_invoice') || lowerName.includes('invoice');
                        if (filterType === 'Packing_List') return lowerName.includes('packing_list') || lowerName.includes('packing');
                        if (filterType === 'Weight_List') return lowerName.includes('weight_list');
                        if (filterType === 'Mill_Certificate') return lowerName.includes('mill_certificate');
                        if (filterType === 'Cargo_Insurance') return lowerName.includes('cargo_insurance') || lowerName.includes('insurance');
                        if (filterType === 'Certificate_Origin') return lowerName.includes('certificate_origin') || lowerName.includes('origin');
                        if (filterType === 'Customs_clearance_Letter') return lowerName.includes('customs_clearance') || lowerName.includes('declaration');
                        if (filterType === 'Delivery_Note') return lowerName.includes('delivery_note') || lowerName.includes('delivery');
                        if (filterType === 'Other') {
                            const knownTypes = ['bill_of_lading', 'b_l', 'commercial_invoice', 'invoice', 'packing_list', 'packing',
                                'weight_list', 'mill_certificate', 'cargo_insurance', 'insurance',
                                'certificate_origin', 'origin', 'customs_clearance', 'declaration', 'delivery_note', 'delivery'];
                            return !knownTypes.some(t => lowerName.includes(t));
                        }
                        return true;
                    });
                    if (filtered.length > 0) files = filtered;
                } else {
                    // 증빙 칼럼 클릭 → original 파일만 표시
                    files = files.filter(f => f.type === 'original');
                }

                const filesWithUrl = files.map(f => ({
                    ...f,
                    url: `/api/projects/${project.id}/files/${f.path}`
                }));

                // 새 창으로 PDF 뷰어 열기
                const viewerData = {
                    files: filesWithUrl,
                    title: filterType
                        ? `${filterType} 문서: ${row.billingDocument}`
                        : `증빙 문서 (원본): ${row.billingDocument}`,
                    timestamp: Date.now()
                };

                localStorage.setItem('pdfViewerPopoutState', JSON.stringify(viewerData));
                window.open('/?mode=viewer', '_blank', 'width=1400,height=900');
            } else {
                alert(filterType
                    ? `해당 전표의 ${filterType} 파일을 찾을 수 없습니다.`
                    : '해당 전표의 원본 증빙 파일을 찾을 수 없습니다.');
            }
        } catch (err) {
            console.error(err);
            alert('증빙 파일을 검색하는데 실패했습니다.');
        }
    };

    const handleUploadEvidence = (row) => {
        setUploadModalState({
            isOpen: true,
            billingDocument: row.billingDocument
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
                setEvidenceData(prev => prev.map(row => {
                    if (row.billingDocument === billingDocument) {
                        return { ...row, evidenceStatus: '완료' };
                    }
                    return row;
                }));
            } else {
                alert('Upload failed: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('Error uploading file');
        }
    };

    const handleDeleteEvidence = async (file) => {
        try {
            const response = await fetch(`/api/projects/${project.id}/evidence/delete`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filepath: file.path })
            });
            const result = await response.json();

            if (response.ok) {
                alert('파일이 삭제되었습니다.');
                setPdfViewerState(prev => ({
                    ...prev,
                    files: prev.files.filter(f => f.path !== file.path)
                }));
            } else {
                alert('파일 삭제 실패: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('파일 삭제 중 오류가 발생했습니다.');
        }
    };

    return (
        <div className="dp-card" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 85px)' }}>
            {showDownloadProgress && (
                <ProgressBar
                    progress={downloadProgress}
                />
            )}
            <div className="dp-dashboard-header" style={{ padding: '1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.5rem' }}>Step 2: Evidence Collection</h1>
                    <p style={{ color: '#64748b' }}>Manage evidence documents and split status.</p>
                </div>
                <div className="dp-panel-controls" style={{ border: 'none', padding: 0, background: 'transparent' }}>
                    <div className="dp-panel-group">
                        <button
                            className="dp-btn dp-btn-primary"
                            onClick={() => {
                                setImportModalTab('dms');
                                setIsImportModalOpen(true);
                            }}
                        >
                            📥 Download Evidence
                        </button>
                        <button
                            className="dp-btn dp-btn-secondary"
                            onClick={handleSplitEvidence}
                            disabled={isLoading}
                        >
                            ✂️ Split PDF
                        </button>
                        <button
                            className={`dp-btn ${project?.steps?.step2?.status === 'completed' ? 'dp-btn-danger' : 'dp-btn-success'}`}
                            onClick={project?.steps?.step2?.status === 'completed' ? handleUnconfirm : handleConfirmStep2}
                            disabled={isLoading || (project?.steps?.step3?.status === 'completed')}
                            style={{ opacity: (project?.steps?.step3?.status === 'completed') ? 0.5 : 1 }}
                        >
                            {project?.steps?.step2?.status === 'completed' ? '↩️ Unconfirm' : '✅ Confirm Evidence'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="dp-summary-bar" style={{ margin: '1.5rem', width: 'auto', flexShrink: 0 }}>
                <div className="dp-summary-item">
                    <span className="dp-summary-label">Total:</span>
                    <span className="dp-summary-value">{evidenceData.length}</span>
                </div>
                <div className="dp-summary-divider"></div>
                <div className="dp-summary-item pending">
                    <span className="dp-summary-label">Collecting:</span>
                    <span className="dp-summary-value" style={{ color: '#d97706' }}>
                        {evidenceData.filter(r => r.evidenceStatus === '수집중').length}
                    </span>
                </div>
                <div className="dp-summary-divider"></div>
                <div className="dp-summary-item match">
                    <span className="dp-summary-label">Completed:</span>
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
                                <th style={{ minWidth: '140px', textAlign: 'left', position: 'sticky', left: '30px', zIndex: 30, background: '#f8fafc', borderRight: '1px solid #e2e8f0', fontSize: '0.8rem' }}>Billing Document</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>Evidence</th>
                                <th style={{ width: '90px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>Status</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Bill of<br />Lading</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Commercial<br />Invoice</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Packing<br />List</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Weight<br />List</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Mill<br />Certificate</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Cargo<br />Insurance</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Certificate<br />of Origin</th>
                                <th style={{ width: '60px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Customs<br />Clearance</th>
                                <th style={{ width: '50px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem' }}>Other</th>
                                <th style={{ width: '100px', textAlign: 'center', fontSize: '0.75rem', padding: '0.5rem 0.25rem', lineHeight: '1.2' }}>Split<br />Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {evidenceData.map((row, index) => (
                                <tr key={row.id}>
                                    <td style={{ textAlign: 'center', position: 'sticky', left: 0, background: 'white', zIndex: 20 }}>
                                        <input
                                            type="checkbox"
                                            checked={selectedRows.has(row.billingDocument)}
                                            onChange={() => handleSelectRow(row.billingDocument)}
                                            style={{ cursor: 'pointer' }}
                                        />
                                    </td>
                                    <td style={{ fontWeight: '500', position: 'sticky', left: '30px', background: 'white', zIndex: 20, borderRight: '1px solid #f1f5f9' }}>
                                        {row.billingDocument}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                                            <span
                                                className="dp-icon-btn"
                                                onClick={() => handleViewEvidence(row)}
                                                title="View Evidence"
                                                style={{ opacity: row.evidenceStatus === '미수집' ? 0.3 : 1 }}
                                            >
                                                📄
                                            </span>
                                            <span
                                                className="dp-icon-btn"
                                                onClick={() => handleUploadEvidence(row)}
                                                title="Upload Evidence"
                                            >
                                                📤
                                            </span>
                                        </div>
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        <span className={`dp-badge ${row.evidenceStatus === '완료' ? 'dp-badge-success' : row.evidenceStatus === '수집중' ? 'dp-badge-pending' : 'dp-badge-error'}`}>
                                            {row.evidenceStatus}
                                        </span>
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Bill_of_Lading === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Bill_of_Lading')} title="View BL">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Commercial_Invoice === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Commercial_Invoice')} title="View Invoice">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Packing_List === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Packing_List')} title="View Packing List">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Weight_List === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Weight_List')} title="View Weight List">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Mill_Certificate === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Mill_Certificate')} title="View Mill Cert">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Cargo_Insurance === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Cargo_Insurance')} title="View Insurance">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Certificate_Origin === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Certificate_Origin')} title="View Origin Cert">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Customs_clearance_Letter === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Customs_clearance_Letter')} title="View Customs">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        {row.Other === 'O' ? (
                                            <span className="dp-icon-btn" onClick={() => handleViewEvidence(row, 'Other')} title="View Other">📄</span>
                                        ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                        <span className={`dp-badge ${row.splitStatus === 'Split 완료' ? 'dp-badge-success' : 'dp-badge-pending'}`}>
                                            {row.splitStatus}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
                    <p>No evidence data available.</p>
                </div>
            )}

            <DataImportModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                onSapFetch={() => { }} // Not used in Step 2
                initialTab={importModalTab}
                project={project}
                currentStep="step2"
                onDMSDownload={handleDMSDownload}
            />

            <EvidenceUploadModal
                isOpen={uploadModalState.isOpen}
                onClose={() => setUploadModalState({ isOpen: false, billingDocument: '' })}
                onUpload={onManualUpload}
                billingDocument={uploadModalState.billingDocument}
            />


        </div>
    );
};

export default Step2EvidenceCollection;
