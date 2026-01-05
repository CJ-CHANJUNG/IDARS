import React from 'react';

const ComparisonTableControls = ({
    stats,
    totalTokens,
    selectedRows,
    onFinalJudgment,
    onSelectAll,
    onSelectByStatus,
    onBulkUpdate,
    filteredData,
    onSaveDraft, // ★ NEW: Save Draft handler
    pendingCount // ★ NEW: Count of pending judgments
}) => {
    console.log('[DEBUG] ComparisonTableControls selectedRows:', selectedRows, 'Size:', selectedRows?.size);

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '0.6rem',
            padding: '0.6rem 1rem',
            background: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
            marginBottom: '0.75rem'
        }}>
            {/* Left: Stats */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <h4 style={{ margin: 0, fontSize: '0.85rem', color: '#1e293b', fontWeight: '700' }}>1차 대사</h4>
                <div style={{ display: 'flex', gap: '0.3rem', fontSize: '0.75rem' }}>
                    <span style={{ padding: '0.15rem 0.4rem', background: '#f1f5f9', color: '#334155', borderRadius: '4px', border: '1px solid #cbd5e1' }}>전체: {stats.total}</span>
                    <span style={{ padding: '0.15rem 0.4rem', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>✅ {stats.complete_match}</span>
                    <span style={{ padding: '0.15rem 0.4rem', background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>⚠️ {stats.partial_error}</span>
                    <span style={{ padding: '0.15rem 0.4rem', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>❌ {stats.review_required}</span>
                    {stats.corrected > 0 && (
                        <span style={{ padding: '0.15rem 0.4rem', background: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', borderRadius: '4px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                            ✏️ {stats.corrected}
                        </span>
                    )}
                    {stats.selected > 0 && (
                        <span style={{ padding: '0.15rem 0.4rem', background: 'rgba(139, 92, 246, 0.15)', color: '#8b5cf6', borderRadius: '4px', border: '1px solid rgba(139, 92, 246, 0.3)' }}>
                            ☑️ {stats.selected}
                        </span>
                    )}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '0.5rem' }}>
                    📊 <span style={{ fontWeight: '600', color: '#3b82f6' }}>📥{totalTokens.input.toLocaleString()}</span> / <span style={{ fontWeight: '600', color: '#10b981' }}>📤{totalTokens.output.toLocaleString()}</span>
                </div>
            </div>

            {/* Right: Action Buttons */}
            <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                {/* Selection Controls */}
                <button
                    onClick={() => onSelectAll && onSelectAll({ target: { checked: true } })}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: '#f8fafc',
                        color: '#334155',
                        border: '1px solid #cbd5e1',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    ☑️ 전체
                </button>
                <button
                    onClick={() => onSelectAll && onSelectAll({ target: { checked: false } })}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: '#f8fafc',
                        color: '#334155',
                        border: '1px solid #cbd5e1',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    ⬜ 해제
                </button>

                {/* Filter Selection */}
                <button
                    onClick={() => onSelectByStatus && onSelectByStatus('complete_match')}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(16, 185, 129, 0.1)',
                        color: '#10b981',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    ✅
                </button>
                <button
                    onClick={() => onSelectByStatus && onSelectByStatus('partial_error')}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(245, 158, 11, 0.1)',
                        color: '#f59e0b',
                        border: '1px solid rgba(245, 158, 11, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    ⚠️
                </button>
                <button
                    onClick={() => onSelectByStatus && onSelectByStatus('review_required')}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(239, 68, 68, 0.1)',
                        color: '#ef4444',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    ❌
                </button>
                <button
                    onClick={() => onSelectByStatus && onSelectByStatus('no_evidence')}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(148, 163, 184, 0.1)',
                        color: '#64748b',
                        border: '1px solid rgba(148, 163, 184, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    🚫
                </button>

                {/* Bulk Update Actions */}
                <button
                    onClick={() => onBulkUpdate && onBulkUpdate('complete_match')}
                    disabled={!selectedRows || selectedRows.size === 0}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(16, 185, 129, 0.1)',
                        color: '#10b981',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                        opacity: (!selectedRows || selectedRows.size === 0) ? 0.5 : 1,
                        transition: 'all 0.2s'
                    }}
                >
                    → ✅
                </button>
                <button
                    onClick={() => onBulkUpdate && onBulkUpdate('partial_error')}
                    disabled={!selectedRows || selectedRows.size === 0}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(245, 158, 11, 0.1)',
                        color: '#f59e0b',
                        border: '1px solid rgba(245, 158, 11, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                        opacity: (!selectedRows || selectedRows.size === 0) ? 0.5 : 1,
                        transition: 'all 0.2s'
                    }}
                >
                    → ⚠️
                </button>
                <button
                    onClick={() => onBulkUpdate && onBulkUpdate('review_required')}
                    disabled={!selectedRows || selectedRows.size === 0}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(239, 68, 68, 0.1)',
                        color: '#ef4444',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                        opacity: (!selectedRows || selectedRows.size === 0) ? 0.5 : 1,
                        transition: 'all 0.2s'
                    }}
                >
                    → ❌
                </button>
                <button
                    onClick={() => onBulkUpdate && onBulkUpdate('no_evidence')}
                    disabled={!selectedRows || selectedRows.size === 0}
                    style={{
                        padding: '0.3rem 0.5rem',
                        background: 'rgba(148, 163, 184, 0.1)',
                        color: '#64748b',
                        border: '1px solid rgba(148, 163, 184, 0.3)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: (!selectedRows || selectedRows.size === 0) ? 'not-allowed' : 'pointer',
                        opacity: (!selectedRows || selectedRows.size === 0) ? 0.5 : 1,
                        transition: 'all 0.2s'
                    }}
                >
                    → 🚫
                </button>

                {/* Save Draft */}
                <button
                    onClick={onSaveDraft}
                    disabled={!pendingCount || pendingCount === 0}
                    style={{
                        padding: '0.4rem 0.7rem',
                        background: (pendingCount > 0) ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' : '#f1f5f9',
                        color: (pendingCount > 0) ? '#ffffff' : '#94a3b8',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '0.8rem',
                        fontWeight: '700',
                        cursor: (pendingCount > 0) ? 'pointer' : 'not-allowed',
                        transition: 'all 0.2s',
                        boxShadow: (pendingCount > 0) ? '0 2px 6px rgba(59, 130, 246, 0.3)' : 'none',
                        marginLeft: '0.3rem'
                    }}
                >
                    💾 저장({pendingCount || 0})
                </button>
            </div>
        </div>
    );
};

export default ComparisonTableControls;
