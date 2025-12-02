import React, { useState, useEffect, useRef } from 'react';
import './PDFViewerModal.css';

const PDFViewerModal = ({ isOpen, onClose, files = [], title, onDelete }) => {
    const [selectedFileIndex, setSelectedFileIndex] = useState(0);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const modalRef = useRef(null);

    useEffect(() => {
        if (isOpen) {
            setSelectedFileIndex(0);
            setPosition({ x: 0, y: 0 }); // Reset position on open
        }
    }, [isOpen, files]);

    useEffect(() => {
        const handleMouseMove = (e) => {
            if (isDragging) {
                setPosition({
                    x: e.clientX - dragOffset.x,
                    y: e.clientY - dragOffset.y
                });
            }
        };

        const handleMouseUp = () => {
            setIsDragging(false);
        };

        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        }

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, dragOffset]);

    if (!isOpen) return null;

    const currentFile = files.length > 0 ? files[selectedFileIndex] : null;

    const handleDeleteClick = (e, file) => {
        e.stopPropagation();
        if (window.confirm(`'${file.filename}' 파일을 삭제하시겠습니까?`)) {
            onDelete(file);
        }
    };

    const handleMouseDown = (e) => {
        // Only allow dragging from the header
        if (e.target.closest('.pdf-modal-header') && !e.target.closest('.close-btn')) {
            setIsDragging(true);
            // Calculate offset relative to the modal's current position
            // We need to account for the initial centering transform if any, but here we use absolute positioning logic
            // or transform. Let's assume the modal is centered via CSS and we add transform.
            // Actually, simpler is to track the mouse offset from the top-left of the modal.

            // However, since we are using transform: translate(x, y), we need to know the initial mouse position relative to the current transform.
            setDragOffset({
                x: e.clientX - position.x,
                y: e.clientY - position.y
            });
        }
    };

    return (
        <div className="pdf-modal-overlay" onClick={onClose}>
            <div
                className="pdf-modal-content"
                onClick={(e) => e.stopPropagation()}
                style={{
                    transform: `translate(${position.x}px, ${position.y}px)`,
                    transition: isDragging ? 'none' : 'transform 0.1s ease-out'
                }}
            >
                <div
                    className="pdf-modal-header"
                    onMouseDown={handleMouseDown}
                    style={{ cursor: 'move', userSelect: 'none' }}
                >
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

                            {/* Extracted Data Panel */}
                            {currentFile && currentFile.extractedData && (
                                <div className="extracted-data-panel" style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '10px' }}>
                                    <div className="sidebar-header">추출 데이터</div>
                                    <div style={{ fontSize: '0.85rem', overflowY: 'auto', maxHeight: '300px' }}>
                                        {Object.entries(currentFile.extractedData).map(([key, value]) => (
                                            <div key={key} style={{ marginBottom: '8px' }}>
                                                <div style={{ fontWeight: '600', color: '#555' }}>{key}</div>
                                                <div style={{ color: '#000', wordBreak: 'break-all' }}>
                                                    {typeof value === 'object' && value !== null
                                                        ? (value.value !== undefined ? `${value.value} ${value.unit || value.currency || ''}` : JSON.stringify(value))
                                                        : (value || '-')}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
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
