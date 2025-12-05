import React, { useState, useEffect } from 'react';
import './ResultsDashboard.css';

const ResultsDashboard = ({ project }) => {
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

    const getStatusColor = (status) => {
        switch (status) {
            case 'MATCH': return '#4caf50';
            case 'MISMATCH': return '#ff9800';
            case 'MISSING_EVIDENCE': return '#f44336';
            default: return '#9e9e9e';
        }
    };

    const filteredResults = results.filter(item => {
        if (filter === 'all') return true;
        if (filter === 'match') return item.Status === 'MATCH';
        if (filter === 'mismatch') return item.Status === 'MISMATCH';
        if (filter === 'missing') return item.Status === 'MISSING_EVIDENCE';
        return true;
    });

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
                <h1>📊 결과 대시보드</h1>
                <p className="project-name">프로젝트: {project?.name || project?.id}</p>
                <button onClick={loadDashboard} className="refresh-btn">
                    🔄 새로고침
                </button>
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
                        <h3>일치</h3>
                        <p className="card-value">{summary?.matched || 0}</p>
                        <p className="card-percentage">
                            {summary?.total ? ((summary.matched / summary.total) * 100).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>

                <div className="summary-card mismatch">
                    <div className="card-icon">⚠️</div>
                    <div className="card-content">
                        <h3>불일치</h3>
                        <p className="card-value">{summary?.mismatched || 0}</p>
                        <p className="card-percentage">
                            {summary?.total ? ((summary.mismatched / summary.total) * 100).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>

                <div className="summary-card missing">
                    <div className="card-icon">❌</div>
                    <div className="card-content">
                        <h3>증빙 누락</h3>
                        <p className="card-value">{summary?.missing || 0}</p>
                        <p className="card-percentage">
                            {summary?.total ? ((summary.missing / summary.total) * 100).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>
            </div>

            {/* Filter Buttons */}
            <div className="filter-controls">
                <button
                    className={filter === 'all' ? 'active' : ''}
                    onClick={() => setFilter('all')}
                >
                    전체 ({results.length})
                </button>
                <button
                    className={filter === 'match' ? 'active' : ''}
                    onClick={() => setFilter('match')}
                >
                    ✅ 일치 ({summary?.matched || 0})
                </button>
                <button
                    className={filter === 'mismatch' ? 'active' : ''}
                    onClick={() => setFilter('mismatch')}
                >
                    ⚠️ 불일치 ({summary?.mismatched || 0})
                </button>
                <button
                    className={filter === 'missing' ? 'active' : ''}
                    onClick={() => setFilter('missing')}
                >
                    ❌ 누락 ({summary?.missing || 0})
                </button>
            </div>

            {/* Results Table */}
            <div className="results-section">
                <h2>상세 결과 ({filteredResults.length})</h2>
                <div className="results-table-container">
                    <table className="results-table">
                        <thead>
                            <tr>
                                <th>상태</th>
                                <th>전표번호</th>
                                <th>금액</th>
                                <th>수량</th>
                                <th>날짜</th>
                                <th>Incoterms</th>
                                <th>메모</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan="7" style={{ textAlign: 'center', padding: '40px' }}>
                                        데이터가 없습니다
                                    </td>
                                </tr>
                            ) : (
                                filteredResults.map((item, idx) => (
                                    <tr key={idx}>
                                        <td>
                                            <span
                                                className="status-badge"
                                                style={{ backgroundColor: getStatusColor(item.Status) }}
                                            >
                                                {item.Status === 'MATCH' ? '일치' :
                                                    item.Status === 'MISMATCH' ? '불일치' : '누락'}
                                            </span>
                                        </td>
                                        <td>{item.Billing_Document}</td>
                                        <td>{item.Amount_Result || '-'}</td>
                                        <td>{item.Quantity_Result || '-'}</td>
                                        <td>{item.Date_Result || '-'}</td>
                                        <td>{item.Incoterms_Result || '-'}</td>
                                        <td className="notes-cell">{item.Notes || ''}</td>
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
