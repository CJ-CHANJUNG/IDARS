import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import LedgerTable from '../LedgerTable';
import ColumnSelector from '../ColumnSelector';
import DataImportModal from '../DataImportModal';

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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/save`, {
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/confirm`, {
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/unconfirm`, {
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
        try {
            const response = await fetch('http://127.0.0.1:5000/api/upload', {
                method: 'POST',
                body: formData,
            });
            const result = await response.json();

            if (response.ok && Array.isArray(result)) {
                setLedgerData(result);
                if (result.length > 0) {
                    const columns = Object.keys(result[0]);
                    const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
                    setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
                }
                alert("파일 업로드 성공! " + result.length + "개의 행을 로드했습니다.");
            } else {
                alert("Failed to load file: " + (result.error || "Unknown error"));
            }
        } catch (error) {
            console.error('[FILE UPLOAD] Error:', error);
            alert("Error uploading file");
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
        try {
            const response = await fetch('http://127.0.0.1:5000/api/sap/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    projectId: project.id,
                    dateFrom: config.dateFrom,
                    dateTo: config.dateTo
                })
            });
            const result = await response.json();

            if (response.ok && Array.isArray(result)) {
                setLedgerData(result);
                if (result.length > 0) {
                    const columns = Object.keys(result[0]);
                    const initialColumns = DEFAULT_COLUMNS.filter(col => columns.includes(col));
                    setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
                }
                alert('SAP 데이터 다운로드 및 로드 완료: ' + result.length + '개의 행');
            } else {
                alert("SAP 데이터 다운로드 실패: " + (result.error || "Unknown error"));
            }
        } catch (error) {
            console.error('[SAP FETCH] Error:', error);
            alert("SAP 데이터 요청 중 오류가 발생했습니다.");
        } finally {
            setIsLoading(false);
            setIsImportModalOpen(false);
        }
    };

    return (
        <>
            <div className="tabs">
                <button
                    className={`tab-button ${activeTab === 'imported' ? 'active' : ''}`}
                    onClick={() => setActiveTab('imported')}
                >
                    Imported Data ({ledgerData.length})
                </button>
                <button
                    className={`tab-button ${activeTab === 'confirmed' ? 'active' : ''}`}
                    onClick={() => setActiveTab('confirmed')}
                >
                    Confirmed Data ({confirmedData.length})
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'imported' && (
                    <>
                        <div className="table-toolbar" style={{
                            padding: '12px',
                            borderBottom: '1px solid #e0e0e0',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: '12px',
                            backgroundColor: '#f5f5f5',
                            flexWrap: 'wrap'
                        }}>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <label style={{
                                    display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer',
                                    padding: '6px 12px', backgroundColor: isEditMode ? '#fff3cd' : 'white',
                                    border: '1px solid #ddd', borderRadius: '4px'
                                }}>
                                    <input type="checkbox" checked={isEditMode} onChange={(e) => setIsEditMode(e.target.checked)} />
                                    <span>Edit Mode</span>
                                </label>

                                <button className="action-button" onClick={() => setIsImportModalOpen(true)}>
                                    📥 데이터 가져오기
                                </button>

                                {isEditMode && (
                                    <>
                                        <button className="action-button" onClick={handleAddRow}>➕ 행 추가</button>
                                        <button className="action-button" onClick={handleDeleteSelected}>🗑️ 선택 삭제</button>
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
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    <button
                                        className="action-button"
                                        onClick={handleSaveProgress}
                                        disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                        title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 수정할 수 없습니다." : "임시 저장"}
                                    >
                                        💾 임시 저장
                                    </button>

                                    {project?.steps?.step1?.status === 'completed' ? (
                                        <button
                                            className="action-button"
                                            onClick={handleUnconfirm}
                                            disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                            style={{ backgroundColor: '#ef4444', color: 'white' }}
                                            title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 취소할 수 없습니다." : "확정 취소"}
                                        >
                                            ↩️ 확정 취소
                                        </button>
                                    ) : (
                                        <button
                                            className="action-button primary"
                                            onClick={handleConfirm}
                                            disabled={isLoading || (project?.steps?.step2?.status === 'completed')}
                                            style={{
                                                backgroundColor: '#4CAF50', color: 'white',
                                                opacity: (project?.steps?.step2?.status === 'completed') ? 0.5 : 1
                                            }}
                                            title={project?.steps?.step2?.status === 'completed' ? "Step 2가 확정되어 수정할 수 없습니다." : "전표 확정"}
                                        >
                                            ✅ 전표 확정
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
                            <div className="empty-state">
                                <p>확정된 데이터가 없습니다.</p>
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
        </>
    );
};

export default Step1InvoiceConfirmation;
