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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step4/run`);
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
            const response = await fetch(`http://127.0.0.1:5000/api/projects/${project.id}/step4/export`);
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
            <div className="dashboard-container">
                <div className="dashboard-loading">
                    <div className="spinner"></div>
                    <p>대시보드 로딩 중...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <div className="dashboard-header">
                <div className="header-title">
                    <h1>📊 결과 대시보드</h1>
                    <p className="project-name">프로젝트: {project?.name || project?.id}</p>
                </div>
                <div className="header-actions">
                    <button onClick={handleDownloadExcel} className="excel-btn">
                        📥 엑셀 다운로드
                    </button>
                    <button onClick={loadDashboard} className="refresh-btn">
                        🔄 새로고침
                    </button>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="summary-cards">
                <div className="summary-card total">
                    <div className="card-icon">📋</div>
                    <div className="card-content">
                        <h3>전체 전표</h3>
                        <p className="card-value">{summary?.total || 0}</p>
                    </div>
                </div>

                <div className="summary-card match">
                    <div className="card-icon">✅</div>
                    <div className="card-content">
                        <h3>일치 (PASS)</h3>
                        <p className="card-value">{summary?.matched || 0}</p>
                        <p className="card-percentage">
                            {summary?.total ? ((summary.matched / summary.total) * 100).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>

                <div className="summary-card mismatch">
                    <div className="card-icon">⚠️</div>
                    <div className="card-content">
                        <h3>불일치 (FAIL)</h3>
                        <p className="card-value">{summary?.mismatched || 0}</p>
                        <p className="card-percentage">
                            {summary?.total ? ((summary.mismatched / summary.total) * 100).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>

                <div className="summary-card missing">
                    <div className="card-icon">❌</div>
                    <div className="card-content">
                        <h3>확인 필요 (WARN/MISSING)</h3>
                        <p className="card-value">{summary?.missing || 0}</p>
                        <p className="card-percentage">
                            {summary?.total ? ((summary.missing / summary.total) * 100).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>
            </div>

            {/* Filter Buttons */}
            <div className="filter-controls">
                <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>
                    전체 ({results.length})
                </button>
                <button className={filter === 'match' ? 'active' : ''} onClick={() => setFilter('match')}>
                    ✅ 일치 ({summary?.matched || 0})
                </button>
                <button className={filter === 'mismatch' ? 'active' : ''} onClick={() => setFilter('mismatch')}>
                    ⚠️ 불일치 ({summary?.mismatched || 0})
                </button>
                <button className={filter === 'missing' ? 'active' : ''} onClick={() => setFilter('missing')}>
                    ❌ 확인필요 ({summary?.missing || 0})
                </button>
            </div>

            {/* Results Table */}
            <div className="results-section">
                <h2>상세 결과 ({filteredResults.length})</h2>
                <div className="results-table-wrapper">
                    <table className="results-table">
                        <thead>
                            <tr>
                                {/* Fixed Headers */}
                                <th className="sticky-col col-1">최종판단</th>
                                <th className="sticky-col col-2">날짜</th>
                                <th className="sticky-col col-3">금액</th>
                                <th className="sticky-col col-4">인코텀즈</th>
                                <th className="sticky-col col-5">수량</th>
                                {/* Scrollable Step 1 Headers */}
                                {step1Columns.map(col => (
                                    <th key={col}>{col}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan={5 + step1Columns.length} style={{ textAlign: 'center', padding: '40px' }}>
                                        데이터가 없습니다
                                    </td>
                                </tr>
                            ) : (
                                filteredResults.map((item, idx) => (
                                    <tr key={idx}>
                                        {/* Fixed Columns */}
                                        <td className="sticky-col col-1" style={{ textAlign: 'center' }}>
                                            <span title={getStatusText(item.final_judgment)} style={{ fontSize: '1.2rem' }}>
                                                {getStatusIcon(item.final_judgment)}
                                            </span>
                                        </td>
                                        <td className={`sticky-col col-2 ${item.date_status === '불일치' ? 'text-red' : 'text-green'}`}>
                                            {item.date_status}
                                        </td>
                                        <td className={`sticky-col col-3 ${item.amount_status === '불일치' ? 'text-red' : 'text-green'}`}>
                                            {item.amount_status}
                                        </td>
                                        <td className={`sticky-col col-4 ${item.incoterms_status === '불일치' ? 'text-red' : 'text-green'}`}>
                                            {item.incoterms_status}
                                        </td>
                                        <td className={`sticky-col col-5 ${item.quantity_status === '불일치' ? 'text-red' : 'text-green'}`}>
                                            {item.quantity_status}
                                        </td>

                                        {/* Scrollable Step 1 Data */}
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
