import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import './ResultsDashboard.css';

const ResultsDashboard = ({ project }) => {
    const {
        DEFAULT_COLUMNS
    } = useProject();

    const [results, setResults] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, match, mismatch, missing

    useEffect(() => {
        if (project?.id) {
            loadDashboard();
        }
    }, [project]);

    const loadDashboard = async () => {
        try {
            setLoading(true);
            const response = await fetch(`/api/projects/${project.id}/step4/run`);
            const data = await response.json();

            if (data.status === 'success') {
                setResults(data.results || []);
                setSummary(data.summary || {});
            }
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            alert('대시보드 로드 실패: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadExcel = async () => {
        try {
            const response = await fetch(`/api/projects/${project.id}/step4/export`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Reconciliation_Results_${project.id}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } else {
                alert('엑셀 다운로드 실패');
            }
        } catch (error) {
            console.error('Download failed:', error);
            alert('다운로드 중 오류 발생');
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'complete_match': return '🟢';
            case 'partial_error': return '🔴';
            case 'review_required': return '🟡';
            default: return '⚪'; // Missing or Unknown
        }
    };

    const getStatusText = (status) => {
        switch (status) {
            case 'complete_match': return 'PASS';
            case 'partial_error': return 'FAIL';
            case 'review_required': return 'WARN';
            default: return '미수집';
        }
    };

    const filteredResults = results.filter(item => {
        if (filter === 'all') return true;
        if (filter === 'match') return item.final_judgment === 'complete_match';
        if (filter === 'mismatch') return item.final_judgment === 'partial_error';
        if (filter === 'missing') return item.final_judgment === 'MISSING' || item.final_judgment === 'review_required';
        return true;
    });

    // Dynamic Columns from Step 1 Data (excluding the fixed ones)
    const fixedColumns = ['final_judgment', 'date_status', 'amount_status', 'incoterms_status', 'quantity_status'];

    // Use DEFAULT_COLUMNS if available, otherwise fallback to dynamic keys
    const step1Columns = DEFAULT_COLUMNS && DEFAULT_COLUMNS.length > 0
        ? DEFAULT_COLUMNS
        : (results.length > 0
            ? Object.keys(results[0]).filter(key => !fixedColumns.includes(key) && !key.startsWith('_'))
            : []);

    if (loading) {
        return (
            <div className="dp-card" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <div style={{ textAlign: 'center', color: '#64748b' }}>
                    <div className="spinner" style={{ border: '4px solid #f3f3f3', borderTop: '4px solid #3498db', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite', margin: '0 auto 1rem' }}></div>
                    <p>Loading Dashboard...</p>
                    <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
                </div>
            </div>
        );
    }

    return (
        <div className="dp-card">
            <div className="dp-dashboard-header" style={{ padding: '1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.5rem' }}>📊 Results Dashboard</h1>
                    <p style={{ color: '#64748b' }}>Project: {project?.name || project?.id}</p>
                </div>
                <div className="dp-panel-controls" style={{ border: 'none', padding: 0, background: 'transparent' }}>
                    <div className="dp-panel-group">
                        <button onClick={handleDownloadExcel} className="dp-btn dp-btn-primary">
                            📥 Download Excel
                        </button>
                        <button onClick={loadDashboard} className="dp-btn dp-btn-secondary">
                            🔄 Refresh
                        </button>
                    </div>
                </div>
            </div>

            <div className="workspace-content" style={{ padding: '1.5rem', height: 'calc(100vh - 180px)', overflow: 'auto' }}>
                {/* Summary Cards */}
                <div className="dp-summary-bar" style={{ marginBottom: '1.5rem', width: '100%', justifyContent: 'space-around' }}>
                    <div className="dp-summary-item">
                        <span className="dp-summary-label">Total</span>
                        <span className="dp-summary-value">{summary?.total || 0}</span>
                    </div>
                    <div className="dp-summary-divider"></div>
                    <div className="dp-summary-item match">
                        <span className="dp-summary-label">Matched</span>
                        <span className="dp-summary-value">{summary?.matched || 0}</span>
                        <span className="dp-summary-sub" style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '0.5rem' }}>
                            ({summary?.total ? ((summary.matched / summary.total) * 100).toFixed(1) : 0}%)
                        </span>
                    </div>
                    <div className="dp-summary-divider"></div>
                    <div className="dp-summary-item mismatch">
                        <span className="dp-summary-label">Mismatch</span>
                        <span className="dp-summary-value">{summary?.mismatched || 0}</span>
                        <span className="dp-summary-sub" style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '0.5rem' }}>
                            ({summary?.total ? ((summary.mismatched / summary.total) * 100).toFixed(1) : 0}%)
                        </span>
                    </div>
                    <div className="dp-summary-divider"></div>
                    <div className="dp-summary-item pending">
                        <span className="dp-summary-label">Review</span>
                        <span className="dp-summary-value">{summary?.missing || 0}</span>
                        <span className="dp-summary-sub" style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '0.5rem' }}>
                            ({summary?.total ? ((summary.missing / summary.total) * 100).toFixed(1) : 0}%)
                        </span>
                    </div>
                </div>

                {/* Filter Buttons */}
                <div className="dp-tabs" style={{ marginBottom: '1rem', borderBottom: '1px solid #e2e8f0', display: 'flex', gap: '1rem' }}>
                    <button
                        className={`dp-tab ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                        style={{
                            padding: '0.75rem 1rem',
                            border: 'none',
                            background: 'transparent',
                            borderBottom: filter === 'all' ? '2px solid #2563eb' : '2px solid transparent',
                            color: filter === 'all' ? '#2563eb' : '#64748b',
                            fontWeight: filter === 'all' ? '600' : '500',
                            cursor: 'pointer'
                        }}
                    >
                        All ({results.length})
                    </button>
                    <button
                        className={`dp-tab ${filter === 'match' ? 'active' : ''}`}
                        onClick={() => setFilter('match')}
                        style={{
                            padding: '0.75rem 1rem',
                            border: 'none',
                            background: 'transparent',
                            borderBottom: filter === 'match' ? '2px solid #2563eb' : '2px solid transparent',
                            color: filter === 'match' ? '#2563eb' : '#64748b',
                            fontWeight: filter === 'match' ? '600' : '500',
                            cursor: 'pointer'
                        }}
                    >
                        ✅ Matched ({summary?.matched || 0})
                    </button>
                    <button
                        className={`dp-tab ${filter === 'mismatch' ? 'active' : ''}`}
                        onClick={() => setFilter('mismatch')}
                        style={{
                            padding: '0.75rem 1rem',
                            border: 'none',
                            background: 'transparent',
                            borderBottom: filter === 'mismatch' ? '2px solid #2563eb' : '2px solid transparent',
                            color: filter === 'mismatch' ? '#2563eb' : '#64748b',
                            fontWeight: filter === 'mismatch' ? '600' : '500',
                            cursor: 'pointer'
                        }}
                    >
                        ⚠️ Mismatch ({summary?.mismatched || 0})
                    </button>
                    <button
                        className={`dp-tab ${filter === 'missing' ? 'active' : ''}`}
                        onClick={() => setFilter('missing')}
                        style={{
                            padding: '0.75rem 1rem',
                            border: 'none',
                            background: 'transparent',
                            borderBottom: filter === 'missing' ? '2px solid #2563eb' : '2px solid transparent',
                            color: filter === 'missing' ? '#2563eb' : '#64748b',
                            fontWeight: filter === 'missing' ? '600' : '500',
                            cursor: 'pointer'
                        }}
                    >
                        ❌ Review ({summary?.missing || 0})
                    </button>
                </div>

                {/* Results Table */}
                <div className="dp-table-wrapper">
                    <table className="dp-table dp-table-bordered">
                        <thead>
                            <tr>
                                <th style={{ width: '80px', textAlign: 'center' }}>Status</th>
                                <th style={{ width: '100px' }}>Date</th>
                                <th style={{ width: '100px' }}>Amount</th>
                                <th style={{ width: '100px' }}>Incoterms</th>
                                <th style={{ width: '100px' }}>Quantity</th>
                                {step1Columns.map(col => (
                                    <th key={col}>{col}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan={5 + step1Columns.length} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                                        No data found
                                    </td>
                                </tr>
                            ) : (
                                filteredResults.map((item, idx) => (
                                    <tr key={idx}>
                                        <td style={{ textAlign: 'center' }}>
                                            <span title={getStatusText(item.final_judgment)} style={{ fontSize: '1.2rem' }}>
                                                {getStatusIcon(item.final_judgment)}
                                            </span>
                                        </td>
                                        <td className={item.date_status === '불일치' ? 'dp-text-danger' : 'dp-text-success'}>
                                            {item.date_status}
                                        </td>
                                        <td className={item.amount_status === '불일치' ? 'dp-text-danger' : 'dp-text-success'}>
                                            {item.amount_status}
                                        </td>
                                        <td className={item.incoterms_status === '불일치' ? 'dp-text-danger' : 'dp-text-success'}>
                                            {item.incoterms_status}
                                        </td>
                                        <td className={item.quantity_status === '불일치' ? 'dp-text-danger' : 'dp-text-success'}>
                                            {item.quantity_status}
                                        </td>
                                        {step1Columns.map(col => (
                                            <td key={col}>{item[col]}</td>
                                        ))}
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default ResultsDashboard;
