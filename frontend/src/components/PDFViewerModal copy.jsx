import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './PDFViewerModal.css';

// Configure PDF worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const PDFViewerModal = ({ isOpen, onClose, files = [], title, onDelete, highlightCoordinates }) => {
    const [selectedFileIndex, setSelectedFileIndex] = useState(0);
    const [position, setPosition] = useState({ x: 100, y: 50 }); // Initial position
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);
    const [pageDimensions, setPageDimensions] = useState(null);

    useEffect(() => {
        if (isOpen) {
            setSelectedFileIndex(0);
            // Keep previous position or reset if needed.
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

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setPageNumber(1);
    };

    const onPageLoadSuccess = (page) => {
        setPageDimensions({
            width: page.width,
            height: page.height
        });
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

    // Calculate highlight style
    const getHighlightStyle = () => {
        if (!highlightCoordinates || !pageDimensions) return null;

        // coordinates: [ymin, xmin, ymax, xmax] (normalized 0-1000)
        const [ymin, xmin, ymax, xmax] = highlightCoordinates;

        const width = pageDimensions.width * scale;
        const height = pageDimensions.height * scale;

        const top = (ymin / 1000) * height;
        const left = (xmin / 1000) * width;
        const boxHeight = ((ymax - ymin) / 1000) * height;
        const boxWidth = ((xmax - xmin) / 1000) * width;

        return {
            position: 'absolute',
            top: `${top}px`,
            left: `${left}px`,
            width: `${boxWidth}px`,
            height: `${boxHeight}px`,
            backgroundColor: 'rgba(255, 255, 0, 0.3)',
            border: '2px solid red',
            zIndex: 10,
            pointerEvents: 'none'
        };
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
                        {currentFile && <span className="current-file-name"> - {currentFile.filename}</span>}
                    </div>
                    <div className="header-controls">
                        <button disabled={pageNumber <= 1} onClick={() => setPageNumber(p => p - 1)}>&lt;</button>
                        <span>{pageNumber} / {numPages || '--'}</span>
                        <button disabled={pageNumber >= numPages} onClick={() => setPageNumber(p => p + 1)}>&gt;</button>
                        <span style={{ margin: '0 10px' }}>|</span>
                        <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))}>-</button>
                        <span>{Math.round(scale * 100)}%</span>
                        <button onClick={() => setScale(s => Math.min(3.0, s + 0.1))}>+</button>
                        <button className="close-btn" onClick={onClose}>&times;</button>
                    </div>
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
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* PDF Viewer Area */}
                    <div className="pdf-viewer-container" style={{
                        width: files.length > 0 ? 'calc(100% - 280px)' : '100%',
                        position: 'relative',
                        overflow: 'auto',
                        display: 'flex',
                        justifyContent: 'center',
                        backgroundColor: '#525659'
                    }}>
                        {currentFile ? (
                            <div style={{ position: 'relative' }}>
                                <Document
                                    file={currentFile.url}
                                    onLoadSuccess={onDocumentLoadSuccess}
                                    loading={<div style={{ color: 'white' }}>Loading PDF...</div>}
                                    error={<div style={{ color: 'white' }}>Failed to load PDF.</div>}
                                >
                                    <Page
                                        pageNumber={pageNumber}
                                        scale={scale}
                                        onLoadSuccess={onPageLoadSuccess}
                                        renderTextLayer={true}
                                        renderAnnotationLayer={true}
                                    />
                                </Document>
                                {highlightCoordinates && getHighlightStyle() && (
                                    <div style={getHighlightStyle()} />
                                )}
                            </div>
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
