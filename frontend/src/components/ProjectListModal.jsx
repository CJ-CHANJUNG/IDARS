import React, { useState, useEffect } from 'react';
import './ProjectListModal.css';

const ProjectListModal = ({ isOpen, onClose, onLoadProject }) => {
    const [projects, setProjects] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

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

    const handleDelete = async (projectId, e) => {
        e.stopPropagation();
        if (!confirm('정말로 이 프로젝트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;

        setIsLoading(true);
        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (response.ok) {
                fetchProjects();
            } else {
                alert('삭제 실패: ' + result.error);
            }
        } catch (err) {
            console.error(err);
            alert('삭제 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content project-list-modal">
                <div className="modal-header">
                    <h2>Load Project</h2>
                    <button className="close-button" onClick={onClose}>×</button>
                </div>
                <div className="modal-body">
                    {isLoading ? (
                        <div className="loading-spinner">Loading...</div>
                    ) : error ? (
                        <div className="error-message">{error}</div>
                    ) : projects.length === 0 ? (
                        <div className="empty-state">No saved projects found.</div>
                    ) : (
                        <div className="project-list">
                            <table className="project-table">
                                <thead>
                                    <tr>
                                        <th>Project Name</th>
                                        <th>Last Updated</th>
                                        <th>Status</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {projects.map(project => (
                                        <tr key={project.id}>
                                            <td className="project-name">{project.name}</td>
                                            <td>{new Date(project.updated_at).toLocaleString()}</td>
                                            <td>
                                                <span className={`status-badge ${project.status}`}>
                                                    {project.status}
                                                </span>
                                            </td>
                                            <td>
                                                <button
                                                    className="action-button primary small"
                                                    onClick={() => onLoadProject(project.id)}
                                                    style={{ marginRight: '8px' }}
                                                >
                                                    Load
                                                </button>
                                                <button
                                                    className="action-button danger small"
                                                    onClick={(e) => handleDelete(project.id, e)}
                                                    style={{ backgroundColor: '#ef4444', color: 'white' }}
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
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
