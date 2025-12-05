import React, { useState, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import DataImportModal from '../DataImportModal';
import PDFViewerModal from '../PDFViewerModal';
import EvidenceUploadModal from '../EvidenceUploadModal';
import ProgressBar from '../ProgressBar';

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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/status`);
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/dms-download`, {
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
                const response = await fetch(`http://127.0.0.1:5000/api/dms/progress/${project.id}`);
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/split-evidence`, {
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
                const response = await fetch(`http://127.0.0.1:5000/api/split/progress/${project.id}`);
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/confirm-step2`, {
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/unconfirm`, {
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/search?billingDocument=${row.billingDocument}`);
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
                    url: `http://127.0.0.1:5000/api/projects/${project.id}/files/${f.path}`
                }));

                setPdfViewerState({
                    isOpen: true,
                    files: filesWithUrl,
                    title: filterType
                        ? `${filterType} 문서: ${row.billingDocument}`
                        : `증빙 문서 (원본): ${row.billingDocument}`,
                    billingDocument: row.billingDocument
                });
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/upload`, {
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/evidence/delete`, {
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
        <>
            <div className="step-header" style={{
                padding: '1.5rem 2rem',
                borderBottom: '1px solid #e0e0e0',
                background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.05) 0%, rgba(6, 182, 212, 0.03) 100%)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#0ea5e9', fontSize: '1.3rem' }}>
                            Step 2: 증빙 수집 (Evidence Collection)
                        </h3>
                        <p style={{ margin: 0, color: '#64748b', fontSize: '0.9rem' }}>
                            전표별 증빙 문서 다운로드 및 분류 상태를 관리합니다
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button
                            className="action-button primary"
                            onClick={() => {
                                setImportModalTab('dms');
                                setIsImportModalOpen(true);
                            }}
                            style={{
                                background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                fontWeight: '600',
                                cursor: 'pointer',
                                boxShadow: '0 2px 8px rgba(14, 165, 233, 0.3)'
                            }}
                        >
                            📥 증빙 다운로드
                        </button>
                        <button
                            className="action-button"
                            onClick={handleSplitEvidence}
                            disabled={isLoading}
                            style={{
                                background: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                fontWeight: '600',
                                cursor: 'pointer',
                                boxShadow: '0 2px 8px rgba(139, 92, 246, 0.3)'
                            }}
                        >
                            ✂️ Split PDF
                        </button>
                        <button
                            className="action-button success"
                            onClick={project?.steps?.step2?.status === 'completed' ? handleUnconfirm : handleConfirmStep2}
                            disabled={isLoading || (project?.steps?.step3?.status === 'completed')}
                            style={{
                                background: project?.steps?.step2?.status === 'completed'
                                    ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                                    : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                fontWeight: '600',
                                cursor: 'pointer',
                                boxShadow: project?.steps?.step2?.status === 'completed'
                                    ? '0 2px 8px rgba(239, 68, 68, 0.3)'
                                    : '0 2px 8px rgba(16, 185, 129, 0.3)',
                                opacity: (project?.steps?.step3?.status === 'completed') ? 0.5 : 1
                            }}
                        >
                            {project?.steps?.step2?.status === 'completed' ? '↩️ 확정 취소' : '✅ 증빙 확정'}
                        </button>
                    </div>
                </div>
            </div>

            {evidenceData.length > 0 ? (
                <div className="evidence-table-container" style={{ padding: '1.5rem' }}>
                    <div style={{
                        overflowX: 'auto',
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        backgroundColor: 'white'
                    }}>
                        <table style={{
                            width: '100%',
                            borderCollapse: 'collapse',
                            fontSize: '0.9rem'
                        }}>
                            <thead>
                                <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e0e0e0' }}>
                                    <th style={{ padding: '1rem', textAlign: 'center', width: '40px' }}>
                                        <input
                                            type="checkbox"
                                            checked={evidenceData.length > 0 && selectedRows.size === evidenceData.length}
                                            onChange={handleSelectAll}
                                            style={{ cursor: 'pointer' }}
                                        />
                                    </th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>전표번호</th>
                                    <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>증빙</th>
                                    <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>증빙상태</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>BL</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>인보이스</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>패킹리스트</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>중량명세서</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>밀시트</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>화물보험증권</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>원산지증명서</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>통관서류</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>납품서</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>기타</th>
                                    <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Split 상태</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>비고</th>
                                </tr>
                            </thead>
                            <tbody>
                                {evidenceData.map((row, index) => (
                                    <tr key={row.id} style={{
                                        borderBottom: '1px solid #f1f5f9',
                                        transition: 'background 0.2s'
                                    }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                                    >
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            <input
                                                type="checkbox"
                                                checked={selectedRows.has(row.billingDocument)}
                                                onChange={() => handleSelectRow(row.billingDocument)}
                                                style={{ cursor: 'pointer' }}
                                            />
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', fontWeight: '500', color: '#1e293b' }}>
                                            {row.billingDocument}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                                                <button
                                                    onClick={() => handleViewEvidence(row)}
                                                    title="증빙 보기"
                                                    style={{
                                                        background: 'none',
                                                        border: 'none',
                                                        cursor: 'pointer',
                                                        fontSize: '1.2rem',
                                                        opacity: row.evidenceStatus === '미수집' ? 0.3 : 1
                                                    }}
                                                >
                                                    📄
                                                </button>
                                                <button
                                                    onClick={() => handleUploadEvidence(row)}
                                                    title="증빙 업로드"
                                                    style={{
                                                        background: 'none',
                                                        border: 'none',
                                                        cursor: 'pointer',
                                                        fontSize: '1.2rem'
                                                    }}
                                                >
                                                    📤
                                                </button>
                                            </div>
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            <select
                                                value={row.evidenceStatus}
                                                onChange={(e) => {
                                                    const newData = [...evidenceData];
                                                    newData[index].evidenceStatus = e.target.value;
                                                    setEvidenceData(newData);
                                                }}
                                                style={{
                                                    padding: '0.375rem 0.75rem',
                                                    borderRadius: '6px',
                                                    border: '1px solid #e0e0e0',
                                                    fontSize: '0.85rem',
                                                    backgroundColor: row.evidenceStatus === '완료' ? '#dcfce7' :
                                                        row.evidenceStatus === '수집중' ? '#fef3c7' : '#f1f5f9'
                                                }}
                                            >
                                                <option value="미수집">미수집</option>
                                                <option value="수집중">수집중</option>
                                                <option value="완료">완료</option>
                                            </select>
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Bill_of_Lading === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Bill_of_Lading')} title="BL 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Commercial_Invoice === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Commercial_Invoice')} title="인보이스 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Packing_List === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Packing_List')} title="패킹리스트 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Weight_List === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Weight_List')} title="중량명세서 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Mill_Certificate === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Mill_Certificate')} title="밀시트 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Cargo_Insurance === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Cargo_Insurance')} title="화물보험증권 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Certificate_Origin === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Certificate_Origin')} title="원산지증명서 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Customs_clearance_Letter === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Customs_clearance_Letter')} title="통관서류 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Delivery_Note === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Delivery_Note')} title="납품서 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            {row.Other === 'O' ? (
                                                <span style={{ cursor: 'pointer', fontSize: '1.2rem' }} onClick={() => handleViewEvidence(row, 'Other')} title="기타 문서 보기">📄</span>
                                            ) : <span style={{ color: '#cbd5e1' }}>-</span>}
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                                            <select
                                                value={row.splitStatus}
                                                onChange={(e) => {
                                                    const newData = [...evidenceData];
                                                    newData[index].splitStatus = e.target.value;
                                                    setEvidenceData(newData);
                                                }}
                                                style={{
                                                    padding: '0.375rem 0.75rem',
                                                    borderRadius: '6px',
                                                    border: '1px solid #e0e0e0',
                                                    fontSize: '0.85rem',
                                                    backgroundColor: row.splitStatus === 'Split 완료' ? '#dcfce7' : '#f1f5f9'
                                                }}
                                            >
                                                <option value="대기중">대기중</option>
                                                <option value="Split 완료">Split 완료</option>
                                            </select>
                                        </td>
                                        <td style={{ padding: '0.875rem 1rem' }}>
                                            <input
                                                type="text"
                                                value={row.notes}
                                                onChange={(e) => {
                                                    const newData = [...evidenceData];
                                                    newData[index].notes = e.target.value;
                                                    setEvidenceData(newData);
                                                }}
                                                placeholder="메모"
                                                style={{
                                                    width: '100%',
                                                    padding: '0.5rem',
                                                    border: '1px solid #e0e0e0',
                                                    borderRadius: '4px',
                                                    fontSize: '0.85rem'
                                                }}
                                            />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Summary Stats */}
                    <div style={{
                        marginTop: '1.5rem',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '1rem'
                    }}>
                        <div style={{
                            padding: '1rem',
                            background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
                            borderRadius: '8px',
                            border: '1px solid #bae6fd'
                        }}>
                            <div style={{ fontSize: '0.85rem', color: '#0369a1', marginBottom: '0.25rem' }}>전체 전표</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#0c4a6e' }}>{evidenceData.length}</div>
                        </div>
                        <div style={{
                            padding: '1rem',
                            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                            borderRadius: '8px',
                            border: '1px solid #fcd34d'
                        }}>
                            <div style={{ fontSize: '0.85rem', color: '#b45309', marginBottom: '0.25rem' }}>수집중</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#78350f' }}>
                                {evidenceData.filter(r => r.evidenceStatus === '수집중').length}
                            </div>
                        </div>
                        <div style={{
                            padding: '1rem',
                            background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
                            borderRadius: '8px',
                            border: '1px solid #86efac'
                        }}>
                            <div style={{ fontSize: '0.85rem', color: '#15803d', marginBottom: '0.25rem' }}>수집 완료</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#14532d' }}>
                                {evidenceData.filter(r => r.evidenceStatus === '완료').length}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="empty-state" style={{
                    padding: '3rem',
                    textAlign: 'center',
                    color: '#94a3b8'
                }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                    <h4 style={{ margin: '0 0 0.5rem 0', color: '#475569' }}>증빙 수집 대상이 없습니다</h4>
                    <p style={{ margin: 0 }}>Step 1에서 전표를 확정해주세요.</p>
                </div>
            )}

            <DataImportModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                onDMSDownload={handleDMSDownload}
                initialTab={importModalTab}
                project={project}
                currentStep="step2"
            />


            {/* Download Progress - Modern ProgressBar (Centered Modal) */}
            {showDownloadProgress && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.6)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        width: '90%',
                        maxWidth: '600px',
                        animation: 'fadeInScale 0.3s ease-out'
                    }}>
                        <ProgressBar progress={downloadProgress} />
                    </div>
                </div>
            )}

            <PDFViewerModal
                isOpen={pdfViewerState.isOpen}
                onClose={() => setPdfViewerState(prev => ({ ...prev, isOpen: false }))}
                files={pdfViewerState.files}
                title={pdfViewerState.title}
                onDelete={handleDeleteEvidence}
            />
            <EvidenceUploadModal
                isOpen={uploadModalState.isOpen}
                onClose={() => setUploadModalState(prev => ({ ...prev, isOpen: false }))}
                onUpload={onManualUpload}
            />
        </>
    );
};

export default Step2EvidenceCollection;
