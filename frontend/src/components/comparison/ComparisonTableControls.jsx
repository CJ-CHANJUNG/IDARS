import React from 'react';

const ComparisonTableControls = ({
    stats,
    totalTokens,
    selectedRows,
    onFinalJudgment,
    onSelectAll,
    onSelectByStatus,
    filteredData
}) => {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
            padding: '0.75rem 1rem',
            background: 'white',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            marginBottom: '0.5rem'
        }}>
            {/* Top Row: Title and Stats */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                    📊 토큰: <span style={{ fontWeight: '600' }}>📥 {totalTokens.input.toLocaleString()}</span> / <span style={{ fontWeight: '600' }}>📤 {totalTokens.output.toLocaleString()}</span>
                </div>
            </div>

            {/* Bottom Row: Bulk Selection Controls and Final Judgment */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid #e2e8f0' }}>
                {/* Bulk Selection Buttons */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', marginRight: '0.5rem' }}>일괄 선택:</span>
                    <button
                        onClick={() => onSelectAll && onSelectAll({ target: { checked: true } })}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#f1f5f9',
                            color: '#475569',
                            border: '1px solid #cbd5e1',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.background = '#e2e8f0'}
                        onMouseOut={(e) => e.target.style.background = '#f1f5f9'}
                    >
                        ☑️ 전체 선택
                    </button>
                    <button
                        onClick={() => onSelectAll && onSelectAll({ target: { checked: false } })}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#f1f5f9',
                            color: '#475569',
                            border: '1px solid #cbd5e1',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.background = '#e2e8f0'}
                        onMouseOut={(e) => e.target.style.background = '#f1f5f9'}
                    >
                        ⬜ 전체 해제
                    </button>
                    <div style={{ width: '1px', height: '20px', background: '#cbd5e1', margin: '0 0.25rem' }}></div>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('complete_match')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#d1fae5',
                            color: '#065f46',
                            border: '1px solid #10b981',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.background = '#a7f3d0'}
                        onMouseOut={(e) => e.target.style.background = '#d1fae5'}
                    >
                        ✅ 일치만
                    </button>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('partial_error')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#fef3c7',
                            color: '#92400e',
                            border: '1px solid #f59e0b',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.background = '#fde68a'}
                        onMouseOut={(e) => e.target.style.background = '#fef3c7'}
                    >
                        ⚠️ 불일치만
                    </button>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('review_required')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#fee2e2',
                            color: '#991b1b',
                            border: '1px solid #ef4444',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.background = '#fecaca'}
                        onMouseOut={(e) => e.target.style.background = '#fee2e2'}
                    >
                        ❌ 오류만
                    </button>
                </div>

                {/* Final Judgment Button */}
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
                        cursor: selectedRows.size > 0 ? 'pointer' : 'not-allowed',
                        transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => selectedRows.size > 0 && (e.target.style.background = '#059669')}
                    onMouseOut={(e) => selectedRows.size > 0 && (e.target.style.background = '#10b981')}
                >
                    ✔️ 선택 항목 최종 판단 ({selectedRows.size})
                </button>
            </div>
        </div>
    );
};

export default ComparisonTableControls;
