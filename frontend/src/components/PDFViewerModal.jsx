import React, { useState, useEffect } from 'react';
import './PDFViewerModal.css';

const PDFViewerModal = ({ isOpen, onClose, files = [], title, onDelete }) => {
    const [selectedFileIndex, setSelectedFileIndex] = useState(0);

    useEffect(() => {
        if (isOpen) {
            setSelectedFileIndex(0);
        }
    }, [isOpen, files]);

    if (!isOpen) return null;

    const currentFile = files.length > 0 ? files[selectedFileIndex] : null;

    const handleDeleteClick = (e, file) => {
        e.stopPropagation();
        if (window.confirm(`'${file.filename}' 파일을 삭제하시겠습니까?`)) {
            onDelete(file);
        }
    };

    return (
        <div className="pdf-modal-overlay" onClick={onClose}>
            <div className="pdf-modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="pdf-modal-header">
                    <div className="header-title">
                        <h3>{title}</h3>
                        {currentFile && <span className="current-file-name"> - {currentFile.filename}</span>}
                    </div>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="pdf-modal-body">
                    {/* Sidebar for multiple files */}
                    {files.length > 0 && (
                        <div className="pdf-sidebar">
                            <div className="sidebar-header">파일 목록 ({files.length})</div>
                            <ul className="file-list">
                                {files.map((file, index) => (
                                    <li
                                        key={index}
                                        className={`file-item ${index === selectedFileIndex ? 'active' : ''}`}
                                        onClick={() => setSelectedFileIndex(index)}
                                    >
                                        <div className="file-item-content">
                                            <span className="file-type-badge">{file.type === 'split' ? 'Split' : 'Original'}</span>
                                            <span className="file-name-text">{file.filename}</span>
                                        </div>
                                        <button
                                            className="delete-file-btn"
                                            onClick={(e) => handleDeleteClick(e, file)}
                                            title="파일 삭제"
                                        >
                                            🗑️
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* PDF Viewer Area */}
                    <div className="pdf-viewer-container" style={{ width: files.length > 0 ? 'calc(100% - 280px)' : '100%' }}>
                        {currentFile ? (
                            <iframe
                                src={currentFile.url}
                                title="PDF Viewer"
                                width="100%"
                                height="100%"
                                style={{ border: 'none' }}
                            />
                        ) : (
                            <div className="no-file-message">
                                <p>표시할 파일이 없습니다.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PDFViewerModal;
