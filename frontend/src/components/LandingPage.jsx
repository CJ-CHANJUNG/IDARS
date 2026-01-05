import React, { useState } from 'react';
import './LandingPage.css';

const LandingPage = ({ onProjectStart, onLoadProject }) => {
    const [step, setStep] = useState('selection'); // 'selection' | 'naming'
    const [selectedWorkflowType, setSelectedWorkflowType] = useState(null); // 'sales_evidence' | 'dterm_arrival'
    const [projectName, setProjectName] = useState('');

    const handleWorkflowSelect = (workflowType) => {
        setSelectedWorkflowType(workflowType);
        setStep('naming');
    };

    const handleCreate = () => {
        if (!projectName.trim()) {
            alert('프로젝트 이름을 입력해주세요.');
            return;
        }
        onProjectStart(projectName, selectedWorkflowType);
    };

    const handleBack = () => {
        setStep('selection');
        setSelectedWorkflowType(null);
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
                            <div className="source-card" onClick={() => handleWorkflowSelect('sales_evidence')}>
                                <div className="card-icon">📊</div>
                                <h3>매출 데이터 불러오기</h3>
                                <p>Invoice + BL 기반 매출 전표 검증</p>
                            </div>
                            <div className="source-card" onClick={() => handleWorkflowSelect('dterm_arrival')}>
                                <div className="card-icon">📦</div>
                                <h3>D조건 데이터 불러오기</h3>
                                <p>도착일 기반 D조건 전표 검증</p>
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
                            {selectedWorkflowType === 'sales_evidence' ? '📊 매출증빙 프로젝트' : '📦 D조건 프로젝트'}
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
