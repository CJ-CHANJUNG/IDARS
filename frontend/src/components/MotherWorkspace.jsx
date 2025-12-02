import React, { useEffect, useState } from 'react';
import './MotherWorkspace.css';

const MotherWorkspace = ({ project, onNavigateToStep, onRefresh }) => {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (project && project.id) {
            loadMotherWorkspaceData();
        }
    }, [project]);

    const loadMotherWorkspaceData = async () => {
        try {
            setLoading(true);
            const response = await fetch(`/api/projects/${project.id}/mother-workspace`);
            const data = await response.json();
            setSummary(data);
        } catch (error) {
            console.error('Failed to load mother workspace data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleUnconfirm = async (stepNumber) => {
        const stepName = `Step ${stepNumber}`;
        const confirmMessage = `⚠️ ${stepName} 확정을 취소하시겠습니까?\n\n❌ 확정 데이터가 수정 가능한 상태로 변경됩니다\n📝 데이터 수정 후 다시 확정해야 합니다\n⚠️ 이후 단계들도 순차 재확정이 필요할 수 있습니다`;

        if (!confirm(confirmMessage)) {
            return;
        }

        try {
            const response = await fetch(`/api/projects/${project.id}/unconfirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step: stepNumber })
            });

            const result = await response.json();

            if (response.ok) {
                alert(`✅ ${stepName} 확정이 취소되었습니다.`);
                if (onRefresh) onRefresh();
                loadMotherWorkspaceData();
            } else {
                alert(`❌ 오류: ${result.error}`);
            }
        } catch (error) {
            console.error('Failed to unconfirm step:', error);
            alert(`❌ 확정 취소 실패: ${error.message}`);
        }
    };

    const getStepStatus = (step) => {
        if (!summary || !summary.project) return 'locked';
        return summary.project.steps[step]?.status || 'locked';
    };

    const getStepStatusIcon = (step) => {
        const status = getStepStatus(step);
        switch (status) {
            case 'completed':
                return '✅';
            case 'in_progress':
                return '🔄';
            case 'pending':
                return '⏳';
            case 'locked':
            default:
                return '🔒';
        }
    };

    const getStepStatusText = (step) => {
        const status = getStepStatus(step);
        switch (status) {
            case 'completed':
                return '완료';
            case 'in_progress':
                return '진행중';
            case 'pending':
                return '대기';
            case 'locked':
            default:
                return '잠김';
        }
    };

    const isStepAccessible = (step) => {
        const status = getStepStatus(step);
        return status !== 'locked';
    };

    if (loading) {
        return (
            <div className="mother-workspace">
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>마더 워크스페이스 로딩 중...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="mother-workspace">
            <div className="workspace-header">
                <h1>📊 마더 워크스페이스</h1>
                <p className="workspace-subtitle">전체 프로젝트 진행 상황 및 단계별 요약</p>
            </div>

            {/* Project Info */}
            <div className="project-info-card">
                <h2>{project.name}</h2>
                <div className="info-row">
                    <span className="label">프로젝트 ID:</span>
                    <span className="value">{project.id}</span>
                </div>
                <div className="info-row">
                    <span className="label">현재 단계:</span>
                    <span className="value">Step {summary?.project?.current_step || 0}</span>
                </div>
                <div className="info-row">
                    <span className="label">상태:</span>
                    <span className={`status-badge ${summary?.project?.status}`}>
                        {summary?.project?.status === 'completed' ? '✅ 완료' : '🔄 진행 중'}
                    </span>
                </div>
            </div>

            {/* Timeline View */}
            <div className="timeline-container">
                <h2>🗓️ 프로젝트 타임라인</h2>
                <div className="timeline">
                    {[1, 2, 3, 4].map((stepNum) => (
                        <div key={stepNum} className={`timeline-step ${getStepStatus(`step${stepNum}`)}`}>
                            <div className="step-icon">{getStepStatusIcon(`step${stepNum}`)}</div>
                            <div className="step-label">Step {stepNum}</div>
                            <div className="step-status">{getStepStatusText(`step${stepNum}`)}</div>
                            {stepNum < 4 && <div className="timeline-connector"></div>}
                        </div>
                    ))}
                </div>
            </div>

            {/* Step Summary Cards */}
            <div className="summary-cards">
                {/* Step 1 */}
                <div className={`summary-card ${getStepStatus('step1')}`}>
                    <div className="card-header">
                        <h3>{getStepStatusIcon('step1')} Step 1: 전표 확정</h3>
                        <span className="status-label">{getStepStatusText('step1')}</span>
                    </div>
                    {summary?.step1_summary ? (
                        <div className="card-content">
                            <div className="stat-row">
                                <span className="stat-label">전표 개수:</span>
                                <span className="stat-value">{summary.step1_summary.invoice_count}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">총 금액:</span>
                                <span className="stat-value">
                                    {summary.step1_summary.total_amount.toLocaleString()} 원
                                </span>
                            </div>
                        </div>
                    ) : (
                        <div className="card-content empty">
                            <p>아직 확정되지 않았습니다</p>
                        </div>
                    )}
                    <div className="card-actions">
                        <button
                            className="btn-navigate"
                            onClick={() => onNavigateToStep(1)}
                            disabled={!isStepAccessible('step1')}
                        >
                            이동
                        </button>
                        {getStepStatus('step1') === 'completed' && (
                            <button
                                className="btn-unconfirm"
                                onClick={() => handleUnconfirm(1)}
                            >
                                확정 취소
                            </button>
                        )}
                    </div>
                </div>

                {/* Step 2 */}
                <div className={`summary-card ${getStepStatus('step2')}`}>
                    <div className="card-header">
                        <h3>{getStepStatusIcon('step2')} Step 2: 증빙 수집</h3>
                        <span className="status-label">{getStepStatusText('step2')}</span>
                    </div>
                    {summary?.step2_summary ? (
                        <div className="card-content">
                            <div className="stat-row">
                                <span className="stat-label">수집률:</span>
                                <span className="stat-value">{summary.step2_summary.collection_rate}%</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">수집 문서:</span>
                                <span className="stat-value">
                                    {summary.step2_summary.collected_documents} / {summary.step2_summary.total_documents}
                                </span>
                            </div>
                            {summary.step2_summary.document_types && (
                                <div className="doc-types">
                                    {Object.entries(summary.step2_summary.document_types).map(([type, count]) => (
                                        <span key={type} className="doc-type-badge">
                                            {type}: {count}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="card-content empty">
                            <p>아직 확정되지 않았습니다</p>
                        </div>
                    )}
                    <div className="card-actions">
                        <button
                            className="btn-navigate"
                            onClick={() => onNavigateToStep(2)}
                            disabled={!isStepAccessible('step2')}
                        >
                            이동
                        </button>
                        {getStepStatus('step2') === 'completed' && (
                            <button
                                className="btn-unconfirm"
                                onClick={() => handleUnconfirm(2)}
                            >
                                확정 취소
                            </button>
                        )}
                    </div>
                </div>

                {/* Step 3 */}
                <div className={`summary-card ${getStepStatus('step3')}`}>
                    <div className="card-header">
                        <h3>{getStepStatusIcon('step3')} Step 3: 데이터 추출</h3>
                        <span className="status-label">{getStepStatusText('step3')}</span>
                    </div>
                    {summary?.step3_summary ? (
                        <div className="card-content">
                            <div className="stat-row">
                                <span className="stat-label">추출 문서:</span>
                                <span className="stat-value">{summary.step3_summary.extracted_documents}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">평균 정확도:</span>
                                <span className="stat-value">{summary.step3_summary.avg_accuracy}%</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">낮은 정확도:</span>
                                <span className="stat-value warning">{summary.step3_summary.low_confidence_count}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="card-content empty">
                            <p>아직 확정되지 않았습니다</p>
                        </div>
                    )}
                    <div className="card-actions">
                        <button
                            className="btn-navigate"
                            onClick={() => onNavigateToStep(3)}
                            disabled={!isStepAccessible('step3')}
                        >
                            이동
                        </button>
                        {getStepStatus('step3') === 'completed' && (
                            <button
                                className="btn-unconfirm"
                                onClick={() => handleUnconfirm(3)}
                            >
                                확정 취소
                            </button>
                        )}
                    </div>
                </div>

                {/* Step 4 */}
                <div className={`summary-card ${getStepStatus('step4')}`}>
                    <div className="card-header">
                        <h3>{getStepStatusIcon('step4')} Step 4: 자동 대사</h3>
                        <span className="status-label">{getStepStatusText('step4')}</span>
                    </div>
                    {summary?.step4_summary ? (
                        <div className="card-content">
                            <div className="stat-row">
                                <span className="stat-label">대사 일치율:</span>
                                <span className="stat-value">{summary.step4_summary.match_rate}%</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">일치:</span>
                                <span className="stat-value success">{summary.step4_summary.matched}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">불일치:</span>
                                <span className="stat-value error">{summary.step4_summary.unmatched}</span>
                            </div>
                            <div className="stat-row">
                                <span className="stat-label">확인 필요:</span>
                                <span className="stat-value warning">{summary.step4_summary.needs_review}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="card-content empty">
                            <p>아직 확정되지 않았습니다</p>
                        </div>
                    )}
                    <div className="card-actions">
                        <button
                            className="btn-navigate"
                            onClick={() => onNavigateToStep(4)}
                            disabled={!isStepAccessible('step4')}
                        >
                            이동
                        </button>
                        {getStepStatus('step4') === 'completed' && (
                            <button
                                className="btn-unconfirm"
                                onClick={() => handleUnconfirm(4)}
                            >
                                확정 취소
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Info Panel */}
            <div className="info-panel">
                <h3>ℹ️ 마더 워크스페이스 안내</h3>
                <ul>
                    <li>모든 단계의 확정 데이터가 실시간으로 누적되어 표시됩니다</li>
                    <li>각 단계의 카드를 클릭하여 해당 단계로 이동할 수 있습니다</li>
                    <li>확정된 단계는 "확정 취소" 버튼으로 수정 가능한 상태로 되돌릴 수 있습니다</li>
                    <li>⚠️ 확정 취소 시 이후 단계들의 재확정이 필요할 수 있습니다</li>
                    <li>순차적 진행이 필요: Step 1 → 2 → 3 → 4</li>
                </ul>
            </div>
        </div>
    );
};

export default MotherWorkspace;
