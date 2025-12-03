import React from 'react';

const ComparisonTableControls = ({
    stats,
    totalTokens,
    selectedRows,
    onFinalJudgment
}) => {
    return (
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.75rem 1rem',
            background: 'white',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            marginBottom: '0.5rem'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <h4 style={{ margin: 0, fontSize: '0.95rem' }}>1차 대사 결과</h4>
                <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.85rem' }}>
                    <span className="stat-badge">전체: {stats.total}</span>
                    <span className="stat-badge stat-match">✅ {stats.complete_match}</span>
                    <span className="stat-badge stat-warning">⚠️ {stats.partial_error}</span>
                    <span className="stat-badge stat-error">❌ {stats.review_required}</span>
                    {stats.corrected > 0 && (
                        <span className="stat-badge" style={{ background: '#dbeafe', color: '#1e40af' }}>
                            ✏️ 수정: {stats.corrected}
                        </span>
                    )}
                    {stats.selected > 0 && (
                        <span className="stat-badge" style={{ background: '#fef3c7', color: '#92400e' }}>
                            ☑️ 선택: {stats.selected}
                        </span>
                    )}
                </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                    📊 토큰: <span style={{ fontWeight: '600' }}>📥 {totalTokens.input.toLocaleString()}</span> / <span style={{ fontWeight: '600' }}>📤 {totalTokens.output.toLocaleString()}</span>
                </div>
                <button
                    onClick={onFinalJudgment}
                    disabled={selectedRows.size === 0}
                    style={{
                        padding: '0.5rem 1rem',
                        background: selectedRows.size > 0 ? '#10b981' : '#cbd5e1',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        cursor: selectedRows.size > 0 ? 'pointer' : 'not-allowed'
                    }}
                >
                    ✔️ 선택 항목 최종 판단 ({selectedRows.size})
                </button>
            </div>
        </div>
    );
};

export default ComparisonTableControls;
