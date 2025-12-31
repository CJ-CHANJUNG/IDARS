import React from 'react';

const ComparisonTableControls = ({
    stats,
    totalTokens,
    selectedRows,
    onFinalJudgment,
    onSelectAll,
    onSelectByStatus,
    onBulkUpdate,
    filteredData
}) => {
    console.log('[DEBUG] ComparisonTableControls selectedRows:', selectedRows, 'Size:', selectedRows?.size);

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
            padding: '1rem 1.5rem',
            background: '#1a1a2e',
            borderRadius: '12px',
            border: '1px solid #2a2a3a',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            marginBottom: '1rem'
        }}>
            {/* Top Row: Title and Stats */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <h4 style={{ margin: 0, fontSize: '1rem', color: '#ffffff', fontWeight: '700' }}>1차 대사 결과</h4>
                    <div style={{ display: 'flex', gap: '0.6rem', fontSize: '0.85rem' }}>
                        <span style={{ padding: '0.2rem 0.6rem', background: '#2d2d3d', color: '#e0e0e0', borderRadius: '6px', border: '1px solid #3a3a4a' }}>전체: {stats.total}</span>
                        <span style={{ padding: '0.2rem 0.6rem', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>✅ {stats.complete_match}</span>
                        <span style={{ padding: '0.2rem 0.6rem', background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>⚠️ {stats.partial_error}</span>
                        <span style={{ padding: '0.2rem 0.6rem', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>❌ {stats.review_required}</span>
                        {stats.corrected > 0 && (
                            <span style={{ padding: '0.2rem 0.6rem', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', borderRadius: '6px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                                ✏️ 수정: {stats.corrected}
                            </span>
                        )}
                        {stats.selected > 0 && (
                            <span style={{ padding: '0.2rem 0.6rem', background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.3)' }}>
                                ☑️ 선택: {stats.selected}
                            </span>
                        )}
                    </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#a0a0b0' }}>
                    📊 토큰: <span style={{ fontWeight: '600', color: '#60a5fa' }}>📥 {totalTokens.input.toLocaleString()}</span> / <span style={{ fontWeight: '600', color: '#34d399' }}>📤 {totalTokens.output.toLocaleString()}</span>
                </div>
            </div>

            {/* Bottom Row: Bulk Selection Controls and Final Judgment */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.75rem', borderTop: '1px solid #2a2a3a' }}>
                {/* Bulk Selection Buttons */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', color: '#a0a0b0', fontWeight: '600', marginRight: '0.5rem' }}>일괄 선택:</span>
                    <button
                        onClick={() => onSelectAll && onSelectAll({ target: { checked: true } })}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#2d2d3d',
                            color: '#e0e0e0',
                            border: '1px solid #3a3a4a',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        ☑️ 전체 선택
                    </button>
                    <button
                        onClick={() => onSelectAll && onSelectAll({ target: { checked: false } })}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: '#2d2d3d',
                            color: '#e0e0e0',
                            border: '1px solid #3a3a4a',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        ⬜ 전체 해제
                    </button>
                    <div style={{ width: '1px', height: '20px', background: '#3a3a4a', margin: '0 0.25rem' }}></div>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('complete_match')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(16, 185, 129, 0.15)',
                            color: '#34d399',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        ✅ 일치만
                    </button>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('partial_error')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(245, 158, 11, 0.15)',
                            color: '#fbbf24',
                            border: '1px solid rgba(245, 158, 11, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        ⚠️ 불일치만
                    </button>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('review_required')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(239, 68, 68, 0.15)',
                            color: '#f87171',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        ❌ 오류만
                    </button>
                    <button
                        onClick={() => onSelectByStatus && onSelectByStatus('no_evidence')}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(148, 163, 184, 0.15)',
                            color: '#94a3b8',
                            border: '1px solid rgba(148, 163, 184, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        🚫 증빙없음
                    </button>
                </div>

                {/* Bulk Action Buttons */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', borderLeft: '1px solid #2a2a3a', paddingLeft: '0.5rem' }}>
                    <span style={{ fontSize: '0.85rem', color: '#a0a0b0', fontWeight: '600', marginRight: '0.25rem' }}>선택 항목 적용:</span>
                    <button
                        onClick={() => onBulkUpdate && onBulkUpdate('complete_match')}
                        disabled={!selectedRows || selectedRows.size === 0}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(16, 185, 129, 0.15)',
                            color: '#34d399',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                            opacity: (!selectedRows || selectedRows.size === 0) ? 0.6 : 1,
                            transition: 'all 0.2s'
                        }}
                    >
                        ✅ 일치
                    </button>
                    <button
                        onClick={() => onBulkUpdate && onBulkUpdate('partial_error')}
                        disabled={!selectedRows || selectedRows.size === 0}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(245, 158, 11, 0.15)',
                            color: '#fbbf24',
                            border: '1px solid rgba(245, 158, 11, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                            opacity: (!selectedRows || selectedRows.size === 0) ? 0.6 : 1,
                            transition: 'all 0.2s'
                        }}
                    >
                        ⚠️ 불일치
                    </button>
                    <button
                        onClick={() => onBulkUpdate && onBulkUpdate('review_required')}
                        disabled={!selectedRows || selectedRows.size === 0}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(239, 68, 68, 0.15)',
                            color: '#f87171',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                            opacity: (!selectedRows || selectedRows.size === 0) ? 0.6 : 1,
                            transition: 'all 0.2s'
                        }}
                    >
                        ❌ 오류
                    </button>
                    <button
                        onClick={() => onBulkUpdate && onBulkUpdate('no_evidence')}
                        disabled={!selectedRows || selectedRows.size === 0}
                        style={{
                            padding: '0.4rem 0.8rem',
                            background: 'rgba(148, 163, 184, 0.15)',
                            color: '#94a3b8',
                            border: '1px solid rgba(148, 163, 184, 0.3)',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                            opacity: (!selectedRows || selectedRows.size === 0) ? 0.6 : 1,
                            transition: 'all 0.2s'
                        }}
                    >
                        🚫 증빙없음
                    </button>
                </div>

                {/* Final Judgment Button */}
                <button
                    onClick={onFinalJudgment}
                    disabled={selectedRows.size === 0}
                    style={{
                        padding: '0.6rem 1.2rem',
                        background: selectedRows.size > 0 ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : '#2d2d3d',
                        color: selectedRows.size > 0 ? '#ffffff' : '#4a4a5a',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '0.9rem',
                        fontWeight: '700',
                        cursor: selectedRows.size > 0 ? 'pointer' : 'not-allowed',
                        transition: 'all 0.2s',
                        boxShadow: selectedRows.size > 0 ? '0 4px 12px rgba(16, 185, 129, 0.3)' : 'none'
                    }}
                >
                    ✔️ 선택 항목 최종 판단({selectedRows.size})
                </button>
            </div>
        </div>
    );
};

export default ComparisonTableControls;
