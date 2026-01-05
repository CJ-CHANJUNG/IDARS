import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './PDFViewerModal.css'; // 기존 스타일 재사용

// Configure PDF worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/**
 * UniversalViewerModal - D조건 증빙 전용 뷰어
 * PDF, PNG, JPG 등 다양한 파일 형식 지원
 */
const UniversalViewerModal = ({ isOpen, onClose, files = [], title }) => {
    const [selectedFileIndex, setSelectedFileIndex] = useState(0);
    const [position, setPosition] = useState({ x: 100, y: 50 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);

    // 파일 타입 감지
    const getFileType = (filename) => {
        if (!filename) return 'unknown';
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'pdf') return 'pdf';
        if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'].includes(ext)) return 'image';
        if (['eml', 'msg'].includes(ext)) return 'email';
        return 'other';
    };

    useEffect(() => {
        if (isOpen) {
            setSelectedFileIndex(0);
            if (position.x === 0 && position.y === 0) {
                setPosition({ x: 100, y: 50 });
            }
            setPageNumber(1);
            setScale(1.0);
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
    const fileType = currentFile ? getFileType(currentFile.filename) : 'unknown';

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setPageNumber(1);
    };

    const handleMouseDown = (e) => {
        if (e.target.closest('.pdf-modal-header') && !e.target.closest('.close-btn')) {
            setIsDragging(true);
            setDragOffset({
                x: e.clientX - position.x,
                y: e.clientY - position.y
            });
        }
    };

    const handlePopOut = () => {
        const viewerState = {
            files,
            title,
            timestamp: Date.now()
        };
        localStorage.setItem('pdfViewerPopoutState', JSON.stringify(viewerState));
        window.open('/?mode=viewer', '_blank', 'width=1400,height=900');
    };

    return (
        <div className="pdf-modal-overlay" onClick={onClose}>
            <div
                className="pdf-modal-content"
                onClick={(e) => e.stopPropagation()}
                style={{
                    transform: `translate(${position.x}px, ${position.y}px)`,
                    transition: isDragging ? 'none' : 'transform 0.1s ease-out',
                }}
            >
                <div
                    className="pdf-modal-header"
                    onMouseDown={handleMouseDown}
                    style={{ cursor: 'move', userSelect: 'none' }}
                >
                    <div className="header-title">
                        <h3>{title}</h3>
                        {currentFile && <span className="current-file-name">- {currentFile.filename}</span>}
                    </div>
                    <div className="header-controls">
                        {fileType === 'pdf' && (
                            <>
                                <button disabled={pageNumber <= 1} onClick={() => setPageNumber(p => p - 1)}>&lt;</button>
                                <span>{pageNumber} / {numPages || '--'}</span>
                                <button disabled={pageNumber >= numPages} onClick={() => setPageNumber(p => p + 1)}>&gt;</button>
                                <span style={{ margin: '0 10px' }}>|</span>
                            </>
                        )}
                        <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))}>-</button>
                        <span>{Math.round(scale * 100)}%</span>
                        <button onClick={() => setScale(s => Math.min(3.0, s + 0.1))}>+</button>
                        <span style={{ margin: '0 10px' }}>|</span>
                        <button onClick={handlePopOut} title="새 창으로 열기">↗️</button>
                        <button className="close-btn" onClick={onClose}>&times;</button>
                    </div>
                </div>

                <div className="pdf-modal-body">
                    {/* Sidebar for multiple files */}
                    {files.length > 0 && (
                        <div className="pdf-sidebar">
                            <div className="sidebar-header">파일 목록 ({files.length})</div>
                            <ul className="file-list">
                                {files.map((file, index) => {
                                    const fType = getFileType(file.filename);
                                    const icon = fType === 'pdf' ? '📄' : fType === 'image' ? '🖼️' : '📎';
                                    return (
                                        <li
                                            key={index}
                                            className={`file-item ${index === selectedFileIndex ? 'active' : ''}`}
                                            onClick={() => setSelectedFileIndex(index)}
                                        >
                                            <div className="file-item-content">
                                                <span className="file-type-badge">{icon} {file.type || 'dterm'}</span>
                                                <span className="file-name-text">{file.filename}</span>
                                            </div>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    )}

                    {/* Viewer Area */}
                    <div className="pdf-viewer-container" style={{
                        width: files.length > 0 ? 'calc(100% - 280px)' : '100%',
                        position: 'relative',
                        overflow: 'auto',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        backgroundColor: '#525659'
                    }}>
                        {currentFile ? (
                            <>
                                {/* PDF 뷰어 */}
                                {fileType === 'pdf' && (
                                    <div style={{ position: 'relative' }}>
                                        <Document
                                            file={currentFile.url}
                                            onLoadSuccess={onDocumentLoadSuccess}
                                            loading={<div style={{ color: 'white' }}>PDF 로딩 중...</div>}
                                            error={<div style={{ color: 'white', padding: '20px' }}>
                                                PDF 로드 실패
                                                <br />
                                                <small>{currentFile.url}</small>
                                            </div>}
                                        >
                                            <Page
                                                pageNumber={pageNumber}
                                                scale={scale}
                                                renderTextLayer={true}
                                                renderAnnotationLayer={true}
                                            />
                                        </Document>
                                    </div>
                                )}

                                {/* 이미지 뷰어 */}
                                {fileType === 'image' && (
                                    <div style={{
                                        position: 'relative',
                                        maxWidth: '100%',
                                        maxHeight: '100%',
                                        overflow: 'auto',
                                        display: 'flex',
                                        justifyContent: 'center',
                                        alignItems: 'center'
                                    }}>
                                        <img
                                            src={currentFile.url}
                                            alt={currentFile.filename}
                                            style={{
                                                transform: `scale(${scale})`,
                                                transformOrigin: 'center center',
                                                transition: 'transform 0.1s ease-out',
                                                maxWidth: 'none',
                                                maxHeight: 'none',
                                                display: 'block'
                                            }}
                                            onError={(e) => {
                                                e.target.style.display = 'none';
                                                e.target.parentElement.innerHTML = `
                                                    <div style="color: white; padding: 20px; text-align: center;">
                                                        <p>이미지 로드 실패</p>
                                                        <small>${currentFile.url}</small>
                                                    </div>
                                                `;
                                            }}
                                        />
                                    </div>
                                )}

                                {/* 기타 파일 타입 */}
                                {(fileType === 'email' || fileType === 'other') && (
                                    <div style={{
                                        color: 'white',
                                        padding: '40px',
                                        textAlign: 'center'
                                    }}>
                                        <p style={{ marginBottom: '20px' }}>
                                            미리보기를 지원하지 않는 파일 형식입니다.
                                        </p>
                                        <p style={{
                                            fontSize: '14px',
                                            color: '#ccc',
                                            marginBottom: '20px'
                                        }}>
                                            {currentFile.filename}
                                        </p>
                                        <a
                                            href={currentFile.url}
                                            download={currentFile.filename}
                                            style={{
                                                display: 'inline-block',
                                                padding: '10px 20px',
                                                backgroundColor: '#007bff',
                                                color: 'white',
                                                textDecoration: 'none',
                                                borderRadius: '4px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            📥 다운로드
                                        </a>
                                    </div>
                                )}

                                {fileType === 'unknown' && (
                                    <div style={{ color: 'white', padding: '20px' }}>
                                        알 수 없는 파일 형식입니다.
                                    </div>
                                )}
                            </>
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

export default UniversalViewerModal;
