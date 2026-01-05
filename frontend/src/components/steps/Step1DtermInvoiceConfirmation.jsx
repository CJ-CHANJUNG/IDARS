import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../../context/ProjectContext';
import LedgerTable from '../LedgerTable';
import ColumnSelector from '../ColumnSelector';
import DataImportModal from '../DataImportModal';
import ProgressBar from '../ProgressBar';

// D조건 전용 기본 컬럼 (전표 데이터 샘플 기준)
const DTERM_DEFAULT_COLUMNS = [
    'Billing No.',      // 전표번호
    'Billing Date',     // 매출인식일
    'ATA Date',         // 실제 도착일 (전표에 기재된)
    'ETA Date',         // 예상 도착일
    'Customer Desc.',   // 거래처명
    'SO Inco',          // Incoterms (DAT, DAP, DDP 등)
    '매출액(Loc)',      // 원화 매출액
    'Curr',             // 통화
    '본부',             // 본부
    '그룹',             // 그룹
    'Vendor Desc.',     // 공급업체
    'REMARK'            // 비고
];

const Step1DtermInvoiceConfirmation = () => {
    const {
        project, setProject,
        ledgerData, setLedgerData,
        confirmedData, setConfirmedData,
        isLoading, setIsLoading,
        visibleColumns, setVisibleColumns,
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

    // --- Initialize visible columns for D-term ---
    useEffect(() => {
        if (ledgerData && ledgerData.length > 0 && visibleColumns.length === 0) {
            const columns = Object.keys(ledgerData[0]);
            const initialColumns = DTERM_DEFAULT_COLUMNS.filter(col => columns.includes(col));
            setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
        }
    }, [ledgerData, visibleColumns.length, setVisibleColumns]);

    // --- Handlers ---
    const handleAddRow = () => {
        if (tableRef.current && tableRef.current.insertRowAboveSelection) {
            tableRef.current.insertRowAboveSelection();
        } else {
            const newRow = {};
            if (ledgerData.length > 0) {
                Object.keys(ledgerData[0]).forEach(key => newRow[key] = '');
            } else {
                DTERM_DEFAULT_COLUMNS.forEach(key => newRow[key] = '');
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
            const initialColumns = DTERM_DEFAULT_COLUMNS.filter(col => columns.includes(col));
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
                setSidebarView('step2');
                alert('✅ D조건 전표가 성공적으로 확정되었습니다!\n\nStep 2 (증빙 수집)로 이동합니다.');
                loadProjectData(project.id);
            } else {
                alert('확정 실패: ' + result.error);
            }
        } catch (err) {
            console.error('[CONFIRM] Error:', err);
            alert('확정 중 오류 발생: ' + err.message);
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
                // Clear confirmed data to show confirm button again
                setConfirmedData([]);
                alert(`✅ Step 1 확정이 취소되었습니다.\n데이터를 수정한 후 다시 확정할 수 있습니다.`);
                await loadProjectData(project.id);
                setActiveTab('imported');
                setIsEditMode(true);
            } else {
                alert('확정 취소 실패: ' + result.error);
            }
        } catch (err) {
            console.error('[UNCONFIRM] Error:', err);
            alert('확정 취소 중 오류 발생: ' + err.message);
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
        setProgressData({ current: 0, total: 100, message: '파일 업로드 중...', status: 'running' });

        try {
            setProgressData({ current: 30, total: 100, message: '파일 업로드 중...', status: 'running' });

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });

            setProgressData({ current: 70, total: 100, message: '데이터 처리 중...', status: 'running' });
            const result = await response.json();

            if (response.ok && Array.isArray(result)) {
                setLedgerData(result);
                if (result.length > 0) {
                    const columns = Object.keys(result[0]);
                    const initialColumns = DTERM_DEFAULT_COLUMNS.filter(col => columns.includes(col));
                    setVisibleColumns(initialColumns.length > 0 ? initialColumns : columns);
                }
                setActiveTab('imported');
                setIsEditMode(true);
                setProgressData({ current: 100, total: 100, message: '완료!', status: 'completed' });
                setTimeout(() => setShowProgress(false), 1500);
                setIsImportModalOpen(false);
            } else {
                throw new Error(result.error || 'Invalid data format');
            }
        } catch (err) {
            console.error(err);
            alert('파일 업로드 실패: ' + err.message);
            setProgressData({ current: 0, total: 100, message: 'Failed', status: 'failed' });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSAPDownload = async (params) => {
        console.log('SAP Download not implemented for D-term workflow');
        alert('D조건 워크플로우에서는 SAP 자동 다운로드가 지원되지 않습니다.\n로컬 파일을 업로드해주세요.');
    };

    // --- UI ---
    const allColumns = ledgerData && ledgerData.length > 0 ? Object.keys(ledgerData[0]) : [];
    const displayData = activeTab === 'confirmed' ? confirmedData : ledgerData;
    const isConfirmed = confirmedData && confirmedData.length > 0;

    return (
        <div className="step-container">
            <div className="step-header">
                <h2>📦 Step 1: D조건 전표 확정</h2>
                <p className="step-description">
                    D조건 전표 데이터를 업로드하고 확정합니다.
                    (Billing Date, ATA Date, ETA Date 등 도착일 관련 정보 포함)
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="tab-navigation">
                <button
                    className={`tab-button ${activeTab === 'imported' ? 'active' : ''}`}
                    onClick={() => setActiveTab('imported')}
                >
                    작업 중 데이터 ({ledgerData?.length || 0})
                </button>
                <button
                    className={`tab-button ${activeTab === 'confirmed' ? 'active' : ''}`}
                    onClick={() => setActiveTab('confirmed')}
                    disabled={!isConfirmed}
                >
                    확정된 데이터 ({confirmedData?.length || 0})
                </button>
            </div>

            {/* Action Buttons */}
            <div className="action-bar">
                <div className="left-actions">
                    <button
                        className="action-button primary"
                        onClick={() => setIsImportModalOpen(true)}
                        disabled={isLoading || (isConfirmed && activeTab === 'confirmed')}
                    >
                        📂 데이터 가져오기
                    </button>
                    <button
                        className="action-button"
                        onClick={handleAddRow}
                        disabled={isLoading || !isEditMode || activeTab === 'confirmed'}
                    >
                        ➕ 행 추가
                    </button>
                    <button
                        className="action-button danger"
                        onClick={handleDeleteSelected}
                        disabled={isLoading || !isEditMode || activeTab === 'confirmed'}
                    >
                        🗑️ 선택 삭제
                    </button>
                    <ColumnSelector
                        allColumns={allColumns}
                        visibleColumns={visibleColumns}
                        onToggle={toggleColumn}
                        onReorder={handleColumnReorder}
                        onReset={resetColumns}
                        disabled={isLoading}
                    />
                </div>
                <div className="right-actions">
                    {activeTab === 'imported' && !isConfirmed && (
                        <>
                            <button
                                className="action-button"
                                onClick={handleSaveProgress}
                                disabled={isLoading || !ledgerData || ledgerData.length === 0}
                            >
                                💾 진행 상황 저장
                            </button>
                            <button
                                className="action-button success"
                                onClick={handleConfirm}
                                disabled={isLoading || !ledgerData || ledgerData.length === 0}
                            >
                                ✅ 확정
                            </button>
                        </>
                    )}
                    {isConfirmed && (
                        <button
                            className="action-button warning"
                            onClick={handleUnconfirm}
                            disabled={isLoading}
                        >
                            ↩️ 확정 취소
                        </button>
                    )}
                </div>
            </div>

            {/* Progress Bar */}
            {showProgress && (
                <ProgressBar
                    current={progressData.current}
                    total={progressData.total}
                    message={progressData.message}
                    status={progressData.status}
                />
            )}

            {/* Ledger Table */}
            {displayData && displayData.length > 0 ? (
                <LedgerTable
                    ref={tableRef}
                    data={displayData}
                    onDataChange={onDataChange}
                    isLoading={isLoading}
                    visibleColumns={visibleColumns}
                    onColumnReorder={handleColumnReorder}
                    isEditMode={isEditMode && activeTab === 'imported' && !isConfirmed}
                />
            ) : (
                <div className="empty-state">
                    <p>📦 D조건 전표 데이터가 없습니다.</p>
                    <p>상단의 "데이터 가져오기" 버튼을 클릭하여 CSV 파일을 업로드하세요.</p>
                    <button
                        className="action-button primary"
                        onClick={() => setIsImportModalOpen(true)}
                        style={{ marginTop: '1rem' }}
                    >
                        📂 데이터 가져오기
                    </button>
                </div>
            )}

            {/* Data Import Modal */}
            <DataImportModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                onFileUpload={handleFileUpload}
                onSAPDownload={handleSAPDownload}
                activeTab={importModalTab}
                setActiveTab={setImportModalTab}
                projectId={project?.id}
            />
        </div>
    );
};

export default Step1DtermInvoiceConfirmation;
