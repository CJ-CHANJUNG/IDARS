import React, { useState } from 'react';
import './DMSDownloadModal.css';

const DMSDownloadModal = ({ isOpen, onClose, project, onDownload }) => {
    const [mode, setMode] = useState('project'); // 'project' | 'manual'
    const [manualDocNumbers, setManualDocNumbers] = useState('');
    const [customFolder, setCustomFolder] = useState('');

    if (!isOpen) return null;

    const handleDownload = () => {
        if (mode === 'project') {
            onDownload({ mode: 'project' });
        } else {
            const docNumbers = manualDocNumbers
                .split(/[\n,;]/)
                .map(num => num.trim())
                .filter(num => num.length > 0);

            if (docNumbers.length === 0) {
                alert('전표번호를 입력해주세요');
                return;
            }

            onDownload({
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
            <div className="modal-content dms-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>📂 DMS 증빙 다운로드</h2>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {/* 모드 선택 */}
                    <div className="mode-selector">
                        <button
                            className={`mode-button ${mode === 'project' ? 'active' : ''}`}
                            onClick={() => setMode('project')}
                        >
                            <span className="mode-icon">📋</span>
                            <div>
                                <div className="mode-title">프로젝트 자동 다운로드</div>
                                <div className="mode-desc">Confirmed Data 기반 자동 수집</div>
                            </div>
                        </button>

                        <button
                            className={`mode-button ${mode === 'manual' ? 'active' : ''}`}
                            onClick={() => setMode('manual')}
                        >
                            <span className="mode-icon">✏️</span>
                            <div>
                                <div className="mode-title">수동 전표번호 입력</div>
                                <div className="mode-desc">전표번호 직접 입력 및 폴더 지정</div>
                            </div>
                        </button>
                    </div>

                    {/* 프로젝트 모드 */}
                    {mode === 'project' && (
                        <div className="mode-content">
                            <div className="info-box">
                                <p><strong>프로젝트:</strong> {project?.name || 'N/A'}</p>
                                <p><strong>저장 위치:</strong> Data/projects/{project?.id}/DMS_Downloads/</p>
                                <p className="info-note">
                                    ℹ️ Confirmed Data에 있는 전표번호들의 증빙을 자동으로 다운로드합니다.
                                    중복 전표는 자동 제거되며, 이미 다운로드된 증빙은 건너뜁니다.
                                </p>
                            </div>
                        </div>
                    )}

                    {/* 수동 입력 모드 */}
                    {mode === 'manual' && (
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
                </div>

                <div className="modal-footer">
                    <button className="btn-secondary" onClick={onClose}>
                        취소
                    </button>
                    <button
                        className="btn-primary"
                        onClick={handleDownload}
                        disabled={mode === 'project' && !project}
                    >
                        다운로드 시작
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DMSDownloadModal;
