import React, { useState } from 'react';
import './LandingPage.css';

const LandingPage = ({ onProjectStart, onLoadProject }) => {
    const [step, setStep] = useState('selection'); // 'selection' | 'naming'
    const [selectedSource, setSelectedSource] = useState(null); // 'local' | 'sap'
    const [projectName, setProjectName] = useState('');

    const handleSourceSelect = (source) => {
        setSelectedSource(source);
        setStep('naming');
    };

    const handleCreate = () => {
        if (!projectName.trim()) {
            alert('프로젝트 이름을 입력해주세요.');
            return;
        }
        onProjectStart(projectName, selectedSource);
    };

    const handleBack = () => {
        setStep('selection');
        setSelectedSource(null);
    };

    return (
        <div className="landing-container">
            <div className="landing-content-wrapper">
                <div className="landing-header">
                    <h1 className="landing-title">IDARS</h1>
                    <p className="landing-subtitle">Intelligent Document-Ledger Auto-Reconciliation System</p>
                </div>

                {step === 'selection' && (
                    <div className="selection-step">
                        <h2 className="step-title">프로젝트 시작하기</h2>
                        <div className="source-cards">
                            <div className="source-card" onClick={() => handleSourceSelect('local')}>
                                <div className="card-icon">📂</div>
                                <h3>로컬 파일 불러오기</h3>
                                <p>CSV, Excel 파일을 업로드하여 분석을 시작합니다.</p>
                            </div>
                            <div className="source-card" onClick={() => handleSourceSelect('sap')}>
                                <div className="card-icon">☁️</div>
                                <h3>SAP 데이터 가져오기</h3>
                                <p>SAP 시스템에서 전표 리스트를 조회하고 다운로드합니다.</p>
                            </div>
                            <div className="source-card" onClick={onLoadProject}>
                                <div className="card-icon">📁</div>
                                <h3>기존 프로젝트 불러오기</h3>
                                <p>이전에 저장된 프로젝트를 불러와서 작업을 계속합니다.</p>
                            </div>
                        </div>
                    </div>
                )}

                {step === 'naming' && (
                    <div className="naming-step">
                        <h2 className="step-title">
                            {selectedSource === 'local' ? '로컬 파일 프로젝트' : 'SAP 연동 프로젝트'}
                        </h2>
                        <div className="input-group">
                            <label>프로젝트 이름</label>
                            <input
                                type="text"
                                value={projectName}
                                onChange={(e) => setProjectName(e.target.value)}
                                placeholder="프로젝트 이름을 입력하세요"
                                autoFocus
                                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                            />
                        </div>
                        <div className="step-actions">
                            <button className="landing-button secondary" onClick={handleBack}>
                                뒤로
                            </button>
                            <button className="landing-button primary" onClick={handleCreate}>
                                프로젝트 생성 및 시작
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default LandingPage;
