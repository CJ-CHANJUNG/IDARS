import React from 'react';
import './ProgressBar.css';

/**
 * 통합 진행률 바 컴포넌트
 * - 세련된 디자인 (애니메이션, 그라데이션)
 * - 상세 진행 정보 표시
 * - 다양한 상태 지원 (running, completed, error)
 */
const ProgressBar = ({ progress }) => {
    if (!progress) return null;

    const { current = 0, total = 0, message = '', status = 'running' } = progress;
    const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

    // 상태별 색상 및 아이콘
    const getStatusConfig = () => {
        switch (status) {
            case 'completed':
                return {
                    icon: '✅',
                    color: '#10b981',
                    gradient: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
                    bgColor: 'rgba(16, 185, 129, 0.1)'
                };
            case 'error':
            case 'failed':
                return {
                    icon: '❌',
                    color: '#ef4444',
                    gradient: 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)',
                    bgColor: 'rgba(239, 68, 68, 0.1)'
                };
            case 'running':
            default:
                return {
                    icon: '⏳',
                    color: '#3b82f6',
                    gradient: 'linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)',
                    bgColor: 'rgba(59, 130, 246, 0.1)'
                };
        }
    };

    const config = getStatusConfig();

    return (
        <div className="progress-bar-container">
            {/* Top Section: Count (Left) and Percentage (Right) */}
            <div className="progress-bar-header">
                <span className="progress-count">
                    {current} / {total}
                </span>
                <span className="progress-percentage">
                    {percentage}%
                </span>
            </div>

            {/* Middle Section: Progress Bar */}
            <div className="progress-bar-track">
                <div
                    className={`progress-bar-fill ${status === 'running' ? 'animated' : ''}`}
                    style={{
                        width: `${percentage}%`,
                        background: config.gradient
                    }}
                />
            </div>

            {/* Bottom Section: Status Message */}
            <div className={`progress-message ${status}`}>
                {message || '처리 중...'}
            </div>
        </div>
    );
};

export default ProgressBar;
