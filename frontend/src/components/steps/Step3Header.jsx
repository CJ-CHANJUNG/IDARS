import React from 'react';
import { useProject } from '../../context/ProjectContext';
import '../DesignPreview.css';

const Step3Header = ({
    onExtractAndCompare,
    onSendToDashboard,
    onSaveDraft,
    hasComparisonResults
}) => {
    const {
        confirmedData,
        isLoading
    } = useProject();

    return (
        <div className="dp-toolbar">
            <div>
                <h3 style={{ margin: '0 0 0.25rem 0', color: '#1e293b', fontSize: '1.1rem', fontWeight: '700' }}>
                    Step 3: 데이터 추출 및 비교
                </h3>
                <p style={{ margin: 0, color: '#64748b', fontSize: '0.85rem' }}>
                    OCR 추출 결과와 SAP 데이터를 비교하고 최종 판단을 확정합니다.
                </p>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                    className="dp-btn dp-btn-secondary"
                    onClick={onSaveDraft}
                >
                    💾 임시 저장
                </button>
                <button
                    className="dp-btn dp-btn-primary"
                    onClick={onExtractAndCompare}
                    disabled={isLoading || !confirmedData || confirmedData.length === 0}
                    style={{ opacity: isLoading ? 0.7 : 1 }}
                >
                    {isLoading ? '추출 중...' : '⚡ 추출 및 비교'}
                </button>
                <button
                    className="dp-btn dp-btn-success"
                    onClick={onSendToDashboard}
                    disabled={!hasComparisonResults}
                    style={{ opacity: !hasComparisonResults ? 0.5 : 1 }}
                >
                    📊 대시보드 전송
                </button>
            </div>
        </div>
    );
};

export default Step3Header;
