import React, { useState, useEffect } from 'react';
import './ProjectListModal.css';

const ProjectListModal = ({ isOpen, onClose, onLoadProject }) => {
    const [projects, setProjects] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [filterType, setFilterType] = useState('all'); // 'all' | 'sales_evidence' | 'dterm_arrival'

    useEffect(() => {
        if (isOpen) {
            fetchProjects();
        }
    }, [isOpen]);

    const fetchProjects = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/projects');
            if (!response.ok) {
                throw new Error('Failed to fetch projects');
            }
            const data = await response.json();
            setProjects(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const [deleteTargetId, setDeleteTargetId] = useState(null); // 삭제 대상 ID 상태

    // 삭제 버튼 클릭 시 (확인 모달 띄우기)
    const handleDeleteClick = (projectId, e) => {
        e.stopPropagation();
        setDeleteTargetId(projectId);
    };

    // 실제 삭제 실행
    const confirmDelete = async () => {
        if (!deleteTargetId) return;

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${deleteTargetId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (response.ok) {
                // alert('프로젝트가 삭제되었습니다.'); // UX상 모달 닫히면서 목록 갱신되면 충분
                fetchProjects();
            } else {
                alert('삭제 실패: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('삭제 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
            setDeleteTargetId(null); // 확인 모달 닫기
        }
    };

    // 워크플로우 타입별 배지 정보
    const getWorkflowBadge = (workflowType) => {
        const badges = {
            'sales_evidence': {
                label: '매출증빙',
                color: '#2563eb',
                bgColor: '#dbeafe',
                icon: '📊'
            },
            'dterm_arrival': {
                label: 'D조건',
                color: '#dc2626',
                bgColor: '#fee2e2',
                icon: '📦'
            }
        };
        return badges[workflowType] || badges['sales_evidence'];
    };

    // 필터링된 프로젝트 목록
    const filteredProjects = projects.filter(project =>
        filterType === 'all' || project.workflow_type === filterType
    );

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content project-list-modal">
                {/* 커스텀 삭제 확인 모달 오버레이 */}
                {deleteTargetId && (
                    <div className="delete-confirm-overlay" onClick={() => setDeleteTargetId(null)}>
                        <div className="delete-confirm-box" onClick={(e) => e.stopPropagation()}>
                            <h3>🚨 프로젝트 삭제</h3>
                            <p>정말로 삭제하시겠습니까?<br />삭제된 데이터는 복구할 수 없습니다.</p>
                            <div className="confirm-actions">
                                <button
                                    className="action-button secondary"
                                    onClick={() => setDeleteTargetId(null)}
                                >
                                    취소
                                </button>
                                <button
                                    className="action-button danger"
                                    onClick={confirmDelete}
                                    style={{ backgroundColor: '#ef4444', color: 'white' }}
                                >
                                    삭제 확인
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="modal-header">
                    <h2>기존 프로젝트 불러오기</h2>
                    <button className="close-button" onClick={onClose}>×</button>
                </div>
                <div className="modal-body">
                    {/* 필터 버튼 */}
                    {!isLoading && !error && projects.length > 0 && (
                        <div className="filter-buttons" style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
                            <button
                                className={`filter-btn ${filterType === 'all' ? 'active' : ''}`}
                                onClick={() => setFilterType('all')}
                                style={{
                                    padding: '6px 12px',
                                    border: filterType === 'all' ? '2px solid #2563eb' : '1px solid #d1d5db',
                                    borderRadius: '6px',
                                    backgroundColor: filterType === 'all' ? '#eff6ff' : 'white',
                                    color: '#1f2937', // Text color fixed
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: filterType === 'all' ? '600' : '400'
                                }}
                            >
                                전체 ({projects.length})
                            </button>
                            <button
                                className={`filter-btn ${filterType === 'sales_evidence' ? 'active' : ''}`}
                                onClick={() => setFilterType('sales_evidence')}
                                style={{
                                    padding: '6px 12px',
                                    border: filterType === 'sales_evidence' ? '2px solid #2563eb' : '1px solid #d1d5db',
                                    borderRadius: '6px',
                                    backgroundColor: filterType === 'sales_evidence' ? '#eff6ff' : 'white',
                                    color: '#1f2937', // Text color fixed
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: filterType === 'sales_evidence' ? '600' : '400'
                                }}
                            >
                                📊 매출증빙 ({projects.filter(p => p.workflow_type === 'sales_evidence' || !p.workflow_type).length})
                            </button>
                            <button
                                className={`filter-btn ${filterType === 'dterm_arrival' ? 'active' : ''}`}
                                onClick={() => setFilterType('dterm_arrival')}
                                style={{
                                    padding: '6px 12px',
                                    border: filterType === 'dterm_arrival' ? '2px solid #dc2626' : '1px solid #d1d5db',
                                    borderRadius: '6px',
                                    backgroundColor: filterType === 'dterm_arrival' ? '#fef2f2' : 'white',
                                    color: '#1f2937', // Text color fixed
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: filterType === 'dterm_arrival' ? '600' : '400'
                                }}
                            >
                                📦 D조건 ({projects.filter(p => p.workflow_type === 'dterm_arrival').length})
                            </button>
                        </div>
                    )}

                    {isLoading && !deleteTargetId ? (
                        <div className="loading-spinner">Loading...</div>
                    ) : error ? (
                        <div className="error-message">{error}</div>
                    ) : projects.length === 0 ? (
                        <div className="empty-state">저장된 프로젝트가 없습니다.</div>
                    ) : filteredProjects.length === 0 ? (
                        <div className="empty-state">
                            {filterType === 'sales_evidence' ? '매출증빙 프로젝트가 없습니다.' : 'D조건 프로젝트가 없습니다.'}
                        </div>
                    ) : (
                        <div className="project-list">
                            <table className="project-table">
                                <thead>
                                    <tr>
                                        <th>유형</th>
                                        <th>프로젝트명</th>
                                        <th>마지막 수정일</th>
                                        <th>상태</th>
                                        <th>액션</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredProjects.map(project => {
                                        const badge = getWorkflowBadge(project.workflow_type);
                                        return (
                                            <tr key={project.id}>
                                                <td>
                                                    <span
                                                        className="workflow-badge"
                                                        style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: '4px',
                                                            padding: '4px 10px',
                                                            borderRadius: '6px',
                                                            fontSize: '0.75rem',
                                                            fontWeight: '600',
                                                            color: badge.color,
                                                            backgroundColor: badge.bgColor,
                                                            whiteSpace: 'nowrap'
                                                        }}
                                                    >
                                                        {badge.icon} {badge.label}
                                                    </span>
                                                </td>
                                                <td className="project-name">{project.name}</td>
                                                <td>{new Date(project.updated_at).toLocaleString('ko-KR')}</td>
                                                <td>
                                                    <span className={`status-badge ${project.status}`}>
                                                        {project.status === 'completed' ? '완료' :
                                                            project.status === 'new' ? '신규' : '진행중'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        className="action-button primary small"
                                                        onClick={() => onLoadProject(project.id)}
                                                        style={{ marginRight: '8px' }}
                                                    >
                                                        불러오기
                                                    </button>
                                                    <button
                                                        className="action-button danger small"
                                                        onClick={(e) => handleDeleteClick(project.id, e)}
                                                        style={{ backgroundColor: '#ef4444', color: 'white' }}
                                                    >
                                                        삭제
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProjectListModal;
