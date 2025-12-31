import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import LedgerTable from '../LedgerTable';
import ColumnSelector from '../ColumnSelector';
import DataImportModal from '../DataImportModal';
import ProgressBar from '../ProgressBar';

const Step1InvoiceConfirmation = () => {
    const {
        project, setProject,
        ledgerData, setLedgerData,
        confirmedData, setConfirmedData,
        isLoading, setIsLoading,
        visibleColumns, setVisibleColumns,
        DEFAULT_COLUMNS,
        setSidebarView,
        loadProjectData
    } = useProject();

    const [activeTab, setActiveTab] = useState('imported');
    const [isEditMode, setIsEditMode] = useState(false);
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const [importModalTab, setImportModalTab] = useState('local');
    const [showProgress, setShowProgress] = useState(false);
    const [progressData, setProgressData] = useState({ current: 0, total: 0, message: '', status: '' });
    const tableRef = useRef(null);

    // --- Handlers ---

    const handleAddRow = () => {
        if (tableRef.current && tableRef.current.insertRowAboveSelection) {
            tableRef.current.insertRowAboveSelection();
        } else {
            const newRow = {};
            if (ledgerData.length > 0) {
                Object.keys(ledgerData[0]).forEach(key => newRow[key] = '');
            } else {
                DEFAULT_COLUMNS.forEach(key => newRow[key] = '');
            }
            const newData = [...ledgerData, newRow];
            setLedgerData(newData);
        }
    };

    const handleDeleteSelected = () => {
        if (tableRef.current) {
            tableRef.current.deleteSelectedRows();
        }
    };

    const handleColumnReorder = (newOrder) => {
        setVisibleColumns(newOrder);
    };

    const toggleColumn = (column) => {
        if (visibleColumns.includes(column)) {
            setVisibleColumns(visibleColumns.filter(c => c !== column));
        } else {
            setVisibleColumns([...visibleColumns, column]);
        }
    };

    const resetColumns = () => {
        if (ledgerData.length > 0) {
            const columns = Object.keys(ledgerData[0]);
            const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
            setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
        }
    };

    const onDataChange = (newData) => {
        setLedgerData(newData);
    };

    const handleSaveProgress = async () => {
        if (!project) return;
        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${project.id}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ledgerData: ledgerData,
                    visibleColumns: visibleColumns
                })
            });
            const result = await response.json();

            if (response.ok) {
                alert('진행 상황이 저장되었습니다.');
            } else {
                alert('저장 실패: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('저장 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleConfirm = async () => {
        if (!project) {
            alert('프로젝트가 로드되지 않았습니다.');
            return;
        }

        if (!ledgerData || ledgerData.length === 0) {
            alert('확정할 데이터가 없습니다. 먼저 데이터를 가져오세요.');
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${project.id}/confirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ledgerData: ledgerData,
                    visibleColumns: visibleColumns
                })
            });
            const result = await response.json();

            if (response.ok) {
                setConfirmedData(ledgerData);
                setActiveTab('confirmed');
                setIsEditMode(false);
                setSidebarView('step2'); // Move to Step 2
                alert('✅ 전표가 성공적으로 확정되었습니다!\n\nStep 2 (증빙 수집)로 이동합니다.');
                // Reload project to update status
                loadProjectData(project.id);
            } else {
                alert('Failed to confirm data: ' + result.error);
            }
        } catch (err) {
            console.error('[CONFIRM] Error:', err);
            alert('Error confirming data: ' + err.message);
        }
        setIsLoading(false);
    };

    const handleUnconfirm = async () => {
        if (!project) return;

        if (!window.confirm(`Step 1 확정을 취소하시겠습니까?\n이후 단계의 데이터가 잠금 해제되거나 영향을 받을 수 있습니다.`)) {
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${project.id}/unconfirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step: 1 })
            });
            const result = await response.json();

            if (response.ok) {
                alert(`✅ Step 1 확정이 취소되었습니다.`);
                await loadProjectData(project.id);
                setActiveTab('imported');
                setIsEditMode(true);
            } else {
                alert('Failed to unconfirm: ' + result.error);
            }
        } catch (err) {
            console.error('[UNCONFIRM] Error:', err);
            alert('Error unconfirming step: ' + err.message);
        }
        setIsLoading(false);
    };

    // --- Import Handlers ---
    const handleFileUpload = async (file) => {
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        if (project?.id) formData.append('projectId', project.id);

        setIsLoading(true);
        setShowProgress(true);
        setProgressData({ current: 0, total: 100, message: 'Uploading file...', status: 'running' });

        try {
            // Simulate progress for better UX
            setProgressData({ current: 30, total: 100, message: 'Uploading file...', status: 'running' });

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });

            setProgressData({ current: 70, total: 100, message: 'Processing data...', status: 'running' });
            const result = await response.json();

            if (response.ok && Array.isArray(result)) {
                setLedgerData(result);
                if (result.length > 0) {
                    const columns = Object.keys(result[0]);
                    const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
                    setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
                }
                setProgressData({ current: 100, total: 100, message: 'Upload complete!', status: 'completed' });
                setTimeout(() => {
                    alert("파일 업로드 성공! " + result.length + "개의 행을 로드했습니다.");
                    setShowProgress(false);
                }, 500);
            } else {
                setProgressData({ current: 100, total: 100, message: 'Upload failed', status: 'error' });
                setTimeout(() => {
                    alert("Failed to load file: " + (result.error || "Unknown error"));
                    setShowProgress(false);
                }, 1000);
            }
        } catch (error) {
            console.error('[FILE UPLOAD] Error:', error);
            setProgressData({ current: 100, total: 100, message: 'Error uploading file', status: 'error' });
            setTimeout(() => {
                alert("Error uploading file");
                setShowProgress(false);
            }, 1000);
        } finally {
            setIsLoading(false);
            setIsImportModalOpen(false);
        }
    };

    const handleSapFetch = async (config) => {
        if (!project?.id) {
            alert('프로젝트가 선택되지 않았습니다.');
            return;
        }
        setIsLoading(true);
        setShowProgress(true);
        setProgressData({ current: 0, total: 100, message: 'Connecting to SAP...', status: 'running' });

        try {
            // Simulate progress
            setTimeout(() => setProgressData({ current: 30, total: 100, message: 'Fetching data...', status: 'running' }), 500);

            const response = await fetch('/api/sap/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    projectId: project.id,
                    dateFrom: config.dateFrom,
                    dateTo: config.dateTo
                })
            });

            setProgressData({ current: 80, total: 100, message: 'Processing response...', status: 'running' });
            const result = await response.json();

            if (response.ok && Array.isArray(result)) {
                setLedgerData(result);
                if (result.length > 0) {
                    const columns = Object.keys(result[0]);
                    const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
                    setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
                }
                setProgressData({ current: 100, total: 100, message: 'Download complete!', status: 'completed' });
                setTimeout(() => {
                    alert('SAP 데이터 다운로드 및 로드 완료: ' + result.length + '개의 행');
                    setShowProgress(false);
                }, 500);
            } else {
                setProgressData({ current: 100, total: 100, message: 'Download failed', status: 'error' });
                setTimeout(() => {
                    alert("SAP 데이터 다운로드 실패: " + (result.error || "Unknown error"));
                    setShowProgress(false);
                }, 1000);
            }
        } catch (error) {
            console.error('[SAP FETCH] Error:', error);
            setProgressData({ current: 100, total: 100, message: 'Connection error', status: 'error' });
            setTimeout(() => {
                alert("SAP 데이터 요청 중 오류가 발생했습니다.");
                setShowProgress(false);
            }, 1000);
        } finally {
            setIsLoading(false);
            setIsImportModalOpen(false);
        }
    };

    // --- Number Formatting Helper ---
    const formatNumber = (value) => {
        if (value === undefined || value === null || value === '') return '-';
        const num = parseFloat(value.toString().replace(/,/g, ''));
        if (isNaN(num)) return value;
        return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    return (
        <div className="dp-card">
            {showProgress && (
                <ProgressBar
                    progress={progressData}
                />
            )}
            <div className="dp-dashboard-header" style={{ padding: '0.75rem 1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.25rem' }}>Step 1: Invoice Confirmation</h1>
                    <p style={{ color: '#64748b', fontSize: '0.875rem', margin: 0 }}>Review and confirm imported invoice data.</p>
                </div>
            </div>
            <div className="preview-tabs" style={{ padding: '0 1.5rem', marginTop: '0', borderBottom: 'none' }}>
                <button
                    className={`preview-tab ${activeTab === 'imported' ? 'active' : ''}`}
                    onClick={() => setActiveTab('imported')}
                    style={{ padding: '0.75rem 1rem', fontSize: '0.9rem' }}
                >
                    Imported Data ({ledgerData.length})
                </button>
                <button
                    className={`preview-tab ${activeTab === 'confirmed' ? 'active' : ''}`}
                    onClick={() => setActiveTab('confirmed')}
                    style={{ padding: '0.75rem 1rem', fontSize: '0.9rem' }}
                >
                    Confirmed Data ({confirmedData.length})
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'imported' && (
                    <>
                        <div className="dp-toolbar" style={{ padding: '0.5rem 1.5rem' }}>
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                                <button
                                    className={`dp-toggle ${isEditMode ? 'active' : ''}`}
                                    onClick={() => setIsEditMode(!isEditMode)}
                                >
                                    {isEditMode ? '✏️ Edit Mode On' : '✏️ Edit Mode'}
                                </button>

                                <button className="dp-btn dp-btn-secondary" onClick={() => setIsImportModalOpen(true)}>
                                    📥 Import Data
                                </button>

                                {isEditMode && (
                                    <>
                                        <button className="dp-btn dp-btn-secondary" onClick={handleAddRow}>➕ Add Row</button>
                                        <button className="dp-btn dp-btn-secondary" onClick={handleDeleteSelected}>🗑️ Delete Selected</button>
                                    </>
                                )}

                                {ledgerData.length > 0 && (
                                    <ColumnSelector
                                        allColumns={Object.keys(ledgerData[0])}
                                        visibleColumns={visibleColumns}
                                        onToggleColumn={toggleColumn}
                                        onReorderColumns={handleColumnReorder}
                                        onReset={resetColumns}
                                    />
                                )}
                            </div>

                            {ledgerData.length > 0 && (
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                        className="dp-btn dp-btn-secondary"
                                        onClick={handleSaveProgress}
                                        disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                        title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 수정할 수 없습니다." : "임시 저장"}
                                    >
                                        💾 Save Draft
                                    </button>

                                    {project?.steps?.step1?.status === 'completed' ? (
                                        <button
                                            className="dp-btn dp-btn-danger"
                                            onClick={handleUnconfirm}
                                            disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                            title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 취소할 수 없습니다." : "확정 취소"}
                                        >
                                            ↩️ Unconfirm
                                        </button>
                                    ) : (
                                        <button
                                            className="dp-btn dp-btn-primary"
                                            onClick={handleConfirm}
                                            disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                            style={{
                                                opacity: (project?.steps?.step2?.status === 'completed') ? 0.5 : 1
                                            }}
                                            title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 수정할 수 없습니다." : "전표 확정"}
                                        >
                                            ✅ Confirm Invoices
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>

                        <LedgerTable
                            ref={tableRef}
                            data={ledgerData}
                            onDataChange={onDataChange}
                            isLoading={isLoading}
                            visibleColumns={visibleColumns}
                            onColumnReorder={handleColumnReorder}
                            isEditMode={isEditMode}
                        />
                    </>
                )}
                {activeTab === 'confirmed' && (
                    <>
                        {confirmedData.length > 0 ? (
                            <LedgerTable
                                data={confirmedData}
                                onDataChange={() => { }} // Read-only
                                isLoading={isLoading}
                                visibleColumns={visibleColumns}
                                onColumnReorder={handleColumnReorder}
                                isEditMode={false}
                            />
                        ) : (
                            <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
                                <p>No confirmed data available.</p>
                            </div>
                        )}
                    </>
                )}
            </div>

            <DataImportModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                onFileUpload={handleFileUpload}
                onSapFetch={handleSapFetch}
                initialTab={importModalTab}
                project={project}
                currentStep="step1"
            />
        </div>
    );
};

export default Step1InvoiceConfirmation;
