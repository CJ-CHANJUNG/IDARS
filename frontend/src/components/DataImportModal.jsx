import React, { useState, useRef, useEffect } from 'react';
import './DataImportModal.css';

const DataImportModal = ({ isOpen, onClose, onFileUpload, onSapFetch, onDMSDownload, initialTab = 'local', project, currentStep = 'step1' }) => {
    const [activeTab, setActiveTab] = useState(initialTab);
    const fileInputRef = useRef(null);
    const [dragActive, setDragActive] = useState(false);

    // SAP Mock State
    const [sapConfig, setSapConfig] = useState({
        companyCode: '1000',
        dateFrom: '2025-10-01',
        dateTo: '2025-10-31'
    });

    // DMS State
    const [dmsMode, setDmsMode] = useState('project'); // 'project' | 'manual'
    const [manualDocNumbers, setManualDocNumbers] = useState('');
    const [customFolder, setCustomFolder] = useState('');

    // Define which tabs are visible for each step
    const step1Tabs = ['local', 'sap'];
    const step2Tabs = ['dms'];

    const availableTabs = currentStep === 'step1' ? step1Tabs : step2Tabs;

    // Reset active tab when modal opens with a new initialTab
    useEffect(() => {
        if (isOpen) {
            // Ensure initial tab is valid for current step
            if (availableTabs.includes(initialTab)) {
                setActiveTab(initialTab);
            } else {
                setActiveTab(availableTabs[0]);
            }
        }
    }, [isOpen, initialTab, currentStep]);

    if (!isOpen) return null;

    // --- Local File Handlers ---
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            console.log("[MODAL] File dropped:", e.dataTransfer.files[0].name);
            onFileUpload(e.dataTransfer.files[0]);
        }
    };

    const handleFileChange = (e) => {
        console.log("[MODAL] File selected:", e.target.files?.[0]?.name);
        if (e.target.files && e.target.files[0]) {
            onFileUpload(e.target.files[0]);
        }
    };

    // --- SAP Handlers ---
    const handleSapSubmit = () => {
        console.log("[MODAL] SAP submit with config:", sapConfig);
        onSapFetch(sapConfig);
    };

    // --- DMS Handlers ---
    const handleDMSDownload = () => {
        if (dmsMode === 'project') {
            onDMSDownload({ mode: 'project' });
        } else {
            const docNumbers = manualDocNumbers
                .split(/[\n,;]/)
                .map(num => num.trim())
                .filter(num => num.length > 0);

            if (docNumbers.length === 0) {
                alert('전표번호를 입력해주세요');
                return;
            }

            onDMSDownload({
                mode: 'manual',
                docNumbers,
                customFolder: customFolder || null
            });
        }
    };

    const handleBrowseFolder = async () => {
        try {
            const response = await fetch('http://127.0.0.1:5000/api/dms/select-folder', {
                method: 'POST'
            });
            const result = await response.json();
            if (result.folder_path) {
                setCustomFolder(result.folder_path);
            }
        } catch (err) {
            alert('폴더 선택 실패: ' + err.message);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>
                        {currentStep === 'step1' ? 'Step 1: 전표 데이터 가져오기' : 'Step 2: 증빙 문서 수집'}
                    </h2>
                    <button className="close-button" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-tabs">
                    {availableTabs.includes('local') && (
                        <button
                            className={`modal-tab ${activeTab === 'local' ? 'active' : ''}`}
                            onClick={() => setActiveTab('local')}
                        >
                            📂 로컬 파일
                        </button>
                    )}
                    {availableTabs.includes('sap') && (
                        <button
                            className={`modal-tab ${activeTab === 'sap' ? 'active' : ''}`}
                            onClick={() => setActiveTab('sap')}
                        >
                            ☁️ SAP 연동
                        </button>
                    )}
                    {availableTabs.includes('dms') && (
                        <button
                            className={`modal-tab ${activeTab === 'dms' ? 'active' : ''}`}
                            onClick={() => setActiveTab('dms')}
                        >
                            📥 DMS 증빙 수집
                        </button>
                    )}
                </div>

                <div className="modal-body">
                    {activeTab === 'local' && (
                        <div
                            className={`upload-area ${dragActive ? 'drag-active' : ''}`}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            <div className="upload-icon">📂</div>
                            <p>파일을 이곳에 드래그하거나 클릭하여 선택하세요</p>
                            <span className="upload-hint">지원 형식: .csv, .xlsx, .xls</span>
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="file-input-hidden"
                                accept=".csv,.xlsx,.xls"
                                onChange={handleFileChange}
                            />
                            <button
                                className="upload-button"
                                onClick={() => fileInputRef.current.click()}
                            >
                                파일 선택
                            </button>
                        </div>
                    )}

                    {activeTab === 'sap' && (
                        <div className="sap-form">
                            <div className="form-group">
                                <label>법인 코드 (Company Code)</label>
                                <input
                                    type="text"
                                    value={sapConfig.companyCode}
                                    onChange={(e) => setSapConfig({ ...sapConfig, companyCode: e.target.value })}
                                />
                            </div>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>시작일 (From)</label>
                                    <input
                                        type="date"
                                        value={sapConfig.dateFrom}
                                        onChange={(e) => setSapConfig({ ...sapConfig, dateFrom: e.target.value })}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>종료일 (To)</label>
                                    <input
                                        type="date"
                                        value={sapConfig.dateTo}
                                        onChange={(e) => setSapConfig({ ...sapConfig, dateTo: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="sap-actions">
                                <button className="sap-button primary" onClick={handleSapSubmit}>
                                    SAP 데이터 조회 및 다운로드
                                </button>
                            </div>
                        </div>
                    )}

                    {activeTab === 'dms' && (
                        <div className="dms-content">
                            {/* 모드 선택 */}
                            <div className="mode-selector">
                                <button
                                    className={`mode-button ${dmsMode === 'project' ? 'active' : ''}`}
                                    onClick={() => setDmsMode('project')}
                                >
                                    <span className="mode-icon">📋</span>
                                    <div>
                                        <div className="mode-title">프로젝트 자동 다운로드</div>
                                        <div className="mode-desc">Confirmed Data 기반 자동 수집</div>
                                    </div>
                                </button>

                                <button
                                    className={`mode-button ${dmsMode === 'manual' ? 'active' : ''}`}
                                    onClick={() => setDmsMode('manual')}
                                >
                                    <span className="mode-icon">✏️</span>
                                    <div>
                                        <div className="mode-title">수동 전표번호 입력</div>
                                        <div className="mode-desc">전표번호 직접 입력 및 폴더 지정</div>
                                    </div>
                                </button>
                            </div>

                            {/* 프로젝트 모드 */}
                            {dmsMode === 'project' && (
                                <div className="mode-content">
                                    <div className="info-box">
                                        <p><strong>프로젝트:</strong> {project?.name || '선택된 프로젝트 없음'}</p>
                                        <p><strong>저장 위치:</strong> {project ? `Data/projects/${project.id}/DMS_Downloads/` : 'N/A'}</p>
                                        <p className="info-note">
                                            ℹ️ Confirmed Data에 있는 전표번호들의 증빙을 자동으로 다운로드합니다.
                                            중복 전표는 자동 제거되며, 이미 다운로드된 증빙은 건너뜁니다.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* 수동 입력 모드 */}
                            {dmsMode === 'manual' && (
                                <div className="mode-content">
                                    <div className="form-group">
                                        <label>전표번호 입력</label>
                                        <textarea
                                            className="doc-numbers-input"
                                            placeholder="전표번호를 입력하세요 (한 줄에 하나씩, 또는 쉼표/세미콜론으로 구분)&#10;&#10;예시:&#10;94459227&#10;94459275&#10;94461716"
                                            rows="8"
                                            value={manualDocNumbers}
                                            onChange={e => setManualDocNumbers(e.target.value)}
                                        />
                                        <div className="input-hint">
                                            {manualDocNumbers.split(/[\n,;]/).filter(n => n.trim()).length}개 전표번호 입력됨
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label>저장 폴더 (선택)</label>
                                        <div className="folder-input-group">
                                            <input
                                                type="text"
                                                className="folder-input"
                                                placeholder="비워두면 Downloads 폴더에 저장됩니다"
                                                value={customFolder}
                                                onChange={e => setCustomFolder(e.target.value)}
                                            />
                                            <button
                                                type="button"
                                                className="browse-button"
                                                onClick={handleBrowseFolder}
                                            >
                                                📁 찾아보기
                                            </button>
                                        </div>
                                        <div className="input-hint">
                                            절대 경로 또는 상대 경로 입력 가능
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="dms-actions">
                                <button
                                    className="dms-button primary"
                                    onClick={handleDMSDownload}
                                    disabled={dmsMode === 'project' && !project}
                                >
                                    다운로드 시작
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DataImportModal;
