import React from 'react';
import './NextStepModal.css';

const NextStepModal = ({ isOpen, onClose, onAutoProcess, onManualStep2, onViewDashboard }) => {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="next-step-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>✅ 전표 확정 완료!</h2>
                    <p>다음 단계를 선택해주세요</p>
                </div>

                <div className="modal-content">
                    <div className="option-card auto" onClick={onAutoProcess}>
                        <div className="option-icon">⚡</div>
                        <div className="option-info">
                            <h3>자동으로 모든 단계 실행</h3>
                            <p>증빙 수집 → 데이터 추출 → 대시보드 전송까지 한 번에 처리합니다</p>
                            <span className="option-badge">권장</span>
                        </div>
                    </div>

                    <div className="option-card manual" onClick={onManualStep2}>
                        <div className="option-icon">📂</div>
                        <div className="option-info">
                            <h3>Step 2: 증빙 수집부터 수동 진행</h3>
                            <p>각 단계를 직접 확인하며 진행합니다</p>
                        </div>
                    </div>

                    <div className="option-card later" onClick={onViewDashboard}>
                        <div className="option-icon">📊</div>
                        <div className="option-info">
                            <h3>나중에 처리 (대시보드 보기)</h3>
                            <p>지금은 확정만 하고, 나중에 이어서 작업합니다</p>
                        </div>
                    </div>
                </div>

                <button className="close-button" onClick={onClose}>
                    닫기
                </button>
            </div>
        </div>
    );
};

export default NextStepModal;
